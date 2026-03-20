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
    logger.info(f"Rot n°{rot.rot_number} créé — {total} participants, {matched} matchés.")
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
        logger.info(f"Rot n°{data['rot_number']} du {data['rot_date']} déjà à jour — ignoré.")
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
    logger.info(f"Rot n°{data['rot_number']} du {data['rot_date']} mis à jour.")
    return existing


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
