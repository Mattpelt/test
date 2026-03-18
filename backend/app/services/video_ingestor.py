import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.settings import Settings
from app.models.user import User
from app.models.video import Video

logger = logging.getLogger(__name__)

# Extensions vidéo reconnues (insensible à la casse)
VIDEO_EXTENSIONS = {".mp4", ".mov", ".insv", ".avi", ".mts", ".lrv", ".360"}


def _find_videos(mount_path: str) -> list[Path]:
    """Parcourt le périphérique monté et retourne tous les fichiers vidéo trouvés."""
    videos = []
    for root, dirs, files in os.walk(mount_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]  # ignorer les dossiers cachés
        for file in files:
            if Path(file).suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(Path(root) / file)
    return videos


def _get_camera_timestamp(file_path: Path) -> datetime:
    """
    Lit l'horodatage d'un fichier vidéo.
    On utilise la date de modification du fichier, qui correspond
    à l'horloge interne de la caméra au moment de l'enregistrement.
    """
    mtime = os.path.getmtime(file_path)
    return datetime.fromtimestamp(mtime)


def ingest_device(device_node: str, serial: str, db: Session) -> None:
    """
    Point d'entrée principal du module d'ingestion.

    1. Cherche le propriétaire de la caméra (via le numéro de série)
    2. Monte le périphérique en lecture seule
    3. Copie les fichiers vidéo vers le stockage
    4. Enregistre chaque vidéo en base de données
    5. Démonte le périphérique
    """

    # --- 1. Identifier le propriétaire ---
    user = (
        db.query(User)
        .filter(User.camera_serials.contains([serial]), User.is_active == True)
        .first()
    )

    if not user:
        logger.warning(
            f"Numéro de série inconnu : {serial}. "
            "Aucun compte associé — onboarding requis (F01/F02)."
        )
        # TODO : notifier l'interface pour déclencher le flux de création de compte
        return

    logger.info(f"Caméra reconnue : {serial} → {user.first_name} {user.last_name}")

    # --- 2. Récupérer la configuration ---
    settings = db.query(Settings).first()
    retention_days = settings.retention_days if settings else 90
    storage_path = settings.video_storage_path if settings else "/mnt/videos"

    # --- 3. Monter le périphérique en lecture seule ---
    mount_point = tempfile.mkdtemp(prefix="camera_")
    try:
        subprocess.run(
            ["mount", "-o", "ro", device_node, mount_point],
            check=True,
            timeout=15,
        )
        logger.info(f"Périphérique monté : {device_node} → {mount_point}")

        # --- 4. Trouver les fichiers vidéo ---
        videos = _find_videos(mount_point)
        logger.info(f"{len(videos)} fichier(s) vidéo trouvé(s) sur {device_node}")

        # --- 5. Copier et enregistrer ---
        ingested = 0
        skipped = 0

        for video_file in videos:
            # Destination : /mnt/videos/{user_id}/{YYYY-MM-DD}/{nom_fichier}
            dest_dir = (
                Path(storage_path)
                / str(user.id)
                / datetime.now().strftime("%Y-%m-%d")
            )
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / video_file.name

            # Ne pas réingérer un fichier déjà présent
            if dest_path.exists():
                skipped += 1
                continue

            # Copie en préservant les métadonnées (dont la date de modification)
            shutil.copy2(video_file, dest_path)

            camera_ts = _get_camera_timestamp(video_file)
            expires_at = datetime.utcnow() + timedelta(days=retention_days)

            db_video = Video(
                file_name=video_file.name,
                file_path=str(dest_path),
                file_format=video_file.suffix.upper().lstrip("."),
                file_size_bytes=video_file.stat().st_size,
                camera_timestamp=camera_ts,
                owner_id=user.id,
                matching_status="UNMATCHED",
                expires_at=expires_at,
            )
            db.add(db_video)
            ingested += 1

        db.commit()
        logger.info(
            f"Ingestion terminée pour {user.first_name} {user.last_name} : "
            f"{ingested} vidéo(s) ingérée(s), {skipped} ignorée(s) (déjà présentes)."
        )

    except subprocess.CalledProcessError as e:
        logger.error(f"Impossible de monter {device_node} : {e}")

    except Exception as e:
        db.rollback()
        logger.error(f"Erreur inattendue lors de l'ingestion : {e}")

    finally:
        # --- 6. Démonter proprement ---
        subprocess.run(["umount", mount_point], timeout=10)
        os.rmdir(mount_point)
        logger.info(f"Périphérique démonté : {device_node}")
