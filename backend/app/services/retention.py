import logging
import os
from datetime import datetime

from app.database import SessionLocal
from app.models.video import Video

logger = logging.getLogger(__name__)


def cleanup_expired_videos() -> None:
    """
    Supprime les vidéos dont la date d'expiration est dépassée.
    - Supprime le fichier physique sur le disque
    - Supprime l'enregistrement en base de données

    Planifié quotidiennement à 03:00 via APScheduler.
    La durée de rétention est configurée dans les settings (retention_days).
    Elle s'applique à l'ingestion : expires_at = ingested_at + retention_days.
    Modifier retention_days dans les settings n'affecte que les futures ingestions.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = db.query(Video).filter(Video.expires_at <= now).all()

        if not expired:
            logger.info("[RETENTION] Aucune vidéo expirée — rien à supprimer.")
            return

        logger.info(f"[RETENTION] ━━━ Début nettoyage — {len(expired)} vidéo(s) expirée(s) ━━━")

        deleted_files = 0
        deleted_records = 0
        errors = 0

        for video in expired:
            # Suppression du fichier physique
            if video.file_path and os.path.exists(video.file_path):
                try:
                    os.remove(video.file_path)
                    deleted_files += 1
                    logger.info(
                        f"[RETENTION] Fichier supprimé : {video.file_path} "
                        f"(expiré le {video.expires_at.strftime('%Y-%m-%d')})"
                    )
                except OSError as e:
                    errors += 1
                    logger.error(f"[RETENTION] Impossible de supprimer {video.file_path} : {e}")
            elif video.file_path:
                logger.warning(f"[RETENTION] Fichier déjà absent : {video.file_path}")

            db.delete(video)
            deleted_records += 1

        db.commit()
        logger.info(
            f"[RETENTION] ━━━ Fin nettoyage — "
            f"{deleted_files} fichier(s) supprimé(s), "
            f"{deleted_records} enregistrement(s) supprimé(s)"
            + (f", {errors} erreur(s)" if errors else "")
            + " ━━━"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"[RETENTION] Erreur inattendue : {e}")
    finally:
        db.close()
