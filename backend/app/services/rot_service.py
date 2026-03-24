import logging

from sqlalchemy.orm import Session

from app.models.rot import Rot
from app.models.rot_participant import RotParticipant
from app.models.user import User

logger = logging.getLogger(__name__)


def persist_rot(data: dict, db: Session, source_pdf_path: str | None = None) -> Rot:
    """
    Crée un rot et ses participants en base.
    Tente de matcher chaque participant avec un compte utilisateur via afifly_name.
    """
    rot = Rot(
        rot_number         = data["rot_number"],
        day_number         = data.get("day_number"),
        rot_date           = data["rot_date"],
        rot_time           = data["rot_time"],
        plane_registration = data.get("plane_registration"),
        pilot              = data.get("pilot"),
        chef_avion         = data.get("chef_avion"),
        source_pdf_path    = source_pdf_path,
        parse_status       = "OK",
    )
    db.add(rot)
    db.flush()

    matched = _add_participants(rot.id, data.get("participants", []), db)
    db.commit()
    db.refresh(rot)

    total = len(data.get("participants", []))
    logger.info(
        f"[ROT] ✚ Créé  — n°{rot.rot_number} | {rot.rot_date} {rot.rot_time} | "
        f"{total} participants ({matched} compte(s) associé(s))"
    )
    return rot


def upsert_rot(data: dict, db: Session, source_pdf_path: str | None = None) -> Rot:
    """
    Crée le rot s'il n'existe pas, ou le met à jour si les données ont changé.
    Utilisé par le poller Gmail pour gérer les renvois de PDF.
    """
    existing = db.query(Rot).filter(
        Rot.rot_number == data["rot_number"],
        Rot.rot_date   == data["rot_date"],
    ).first()

    if not existing:
        return persist_rot(data, db, source_pdf_path)

    # Vérifier si les champs principaux ont changé
    fields_changed = any([
        str(existing.rot_time)          != str(data.get("rot_time", "")),
        existing.plane_registration     != data.get("plane_registration"),
        existing.pilot                  != data.get("pilot"),
        existing.chef_avion             != data.get("chef_avion"),
    ])

    existing_names = {
        p.afifly_name
        for p in db.query(RotParticipant).filter(RotParticipant.rot_id == existing.id).all()
    }
    new_names = {p["afifly_name"] for p in data.get("participants", [])}
    participants_changed = existing_names != new_names

    if not fields_changed and not participants_changed:
        logger.info(
            f"[ROT] ↩ Ignoré — n°{data['rot_number']} du {data['rot_date']} déjà en base et à jour "
            f"(reçu à nouveau, probablement via email — aucune action nécessaire)"
        )
        return existing

    if fields_changed:
        existing.rot_time           = data.get("rot_time", existing.rot_time)
        existing.plane_registration = data.get("plane_registration", existing.plane_registration)
        existing.pilot              = data.get("pilot", existing.pilot)
        existing.chef_avion         = data.get("chef_avion", existing.chef_avion)

    if participants_changed:
        db.query(RotParticipant).filter(RotParticipant.rot_id == existing.id).delete()
        _add_participants(existing.id, data.get("participants", []), db)

    db.commit()
    db.refresh(existing)
    logger.info(
        f"[ROT] ✎ Mis à jour — n°{data['rot_number']} du {data['rot_date']} "
        f"({'champs + ' if fields_changed else ''}{'participants' if participants_changed else 'champs'})"
    )
    return existing


def rematch_user_participants(user: User, db: Session) -> int:
    """
    Associe rétroactivement les RotParticipant dont l'afifly_name correspond
    à cet utilisateur et dont le user_id est encore NULL.
    Retourne le nombre de lignes mises à jour.
    """
    if not user.afifly_name:
        return 0
    updated = (
        db.query(RotParticipant)
        .filter(RotParticipant.afifly_name == user.afifly_name, RotParticipant.user_id == None)
        .update({"user_id": user.id})
    )
    if updated:
        db.commit()
        logger.info(f"[ROT] Rematch — {updated} participant(s) liés à {user.afifly_name} (user id={user.id})")
    return updated


def rematch_all_participants(db: Session) -> int:
    """
    Pour chaque utilisateur actif avec un afifly_name, lie les RotParticipant non matchés.
    Retourne le nombre total de lignes mises à jour.
    """
    users = db.query(User).filter(User.afifly_name != None, User.is_active == True).all()
    total = 0
    for user in users:
        total += rematch_user_participants(user, db)
    logger.info(f"[ROT] Rematch global — {total} participant(s) liés au total")
    return total


def _add_participants(rot_id: int, participants: list, db: Session) -> int:
    """Crée les lignes RotParticipant et retourne le nombre de matchés."""
    matched = 0
    for p in participants:
        user = (
            db.query(User)
            .filter(User.afifly_name == p["afifly_name"], User.is_active == True)
            .first()
        )
        if user:
            matched += 1
        db.add(RotParticipant(
            rot_id      = rot_id,
            user_id     = user.id if user else None,
            afifly_name = p["afifly_name"],
            level       = p.get("level"),
            weight      = p.get("weight"),
            jump_type   = p.get("jump_type"),
            group_id    = p.get("group_id", 1),
        ))
    return matched
