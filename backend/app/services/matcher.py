import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.rot import Rot
from app.models.rot_participant import RotParticipant
from app.models.settings import Settings

logger = logging.getLogger(__name__)


def match_videos_to_rots(
    videos: list[tuple[str, int]],  # [(filename, cre_unix_timestamp), ...]
    user_id: int,
    db: Session,
) -> dict[str, tuple[int, int] | None]:  # filename → (rot_id, group_id) | None
    """
    Associe chaque vidéo au rot le plus probable pour cet utilisateur.

    Algorithme :
      Pour chaque vidéo, on cherche tous les rots où :
        - l'utilisateur est participant (rot_participants.user_id = user_id)
        - rot_time ≤ video.cre ≤ rot_time + jump_window_hours
      Parmi les candidats, on retient celui dont le score est minimal :
        score = |video.cre - (rot_time + jump_target_delta_min)|
      Plusieurs vidéos peuvent être associées au même rot (camera allumée 2x pendant un saut).
    """
    settings = db.query(Settings).first()
    target_delta = timedelta(minutes=settings.jump_target_delta_min if settings else 30)
    window = timedelta(hours=settings.jump_window_hours if settings else 2)

    # Récupérer tous les rots où l'utilisateur est participant
    records = (
        db.query(RotParticipant, Rot)
        .join(Rot, RotParticipant.rot_id == Rot.id)
        .filter(RotParticipant.user_id == user_id)
        .all()
    )

    if not records:
        logger.warning(f"[MATCHING] Aucun rot en base pour user_id={user_id} — toutes les vidéos seront ignorées")
        return {filename: None for filename, _ in videos}

    result: dict[str, tuple[int, int] | None] = {}

    for filename, cre_ts in videos:
        video_dt = datetime.fromtimestamp(cre_ts)
        best_score = float("inf")
        best_rot_id = None
        best_group_id = None

        for participant, rot in records:
            rot_dt = datetime.combine(rot.rot_date, rot.rot_time)
            if not (rot_dt <= video_dt <= rot_dt + window):
                continue
            score = abs((video_dt - (rot_dt + target_delta)).total_seconds())
            if score < best_score:
                best_score = score
                best_rot_id = rot.id
                best_group_id = participant.group_id

        if best_rot_id:
            logger.info(
                f"[MATCHING] ✔ {filename} (horodatage {video_dt.strftime('%Y-%m-%d %H:%M:%S')}) "
                f"→ rot #{best_rot_id} (écart {best_score/60:.1f} min par rapport à la cible)"
            )
        else:
            logger.warning(
                f"[MATCHING] ✘ {filename} (horodatage {video_dt.strftime('%Y-%m-%d %H:%M:%S')}) "
                f"— aucun rot dans la fenêtre de {window} — vidéo ignorée"
            )

        result[filename] = (best_rot_id, best_group_id) if best_rot_id else None

    return result
