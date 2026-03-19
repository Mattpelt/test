import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import gphoto2 as gp
from sqlalchemy.orm import Session

from app.models.settings import Settings
from app.models.user import User
from app.models.video import Video

logger = logging.getLogger(__name__)

# Extensions vidéo reconnues (insensible à la casse)
VIDEO_EXTENSIONS = {".mp4", ".mov", ".insv", ".avi", ".mts", ".lrv", ".360"}


# ---------------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------------

def _get_settings(db: Session) -> tuple[int, str]:
    """Retourne (retention_days, storage_path) depuis la table settings."""
    settings = db.query(Settings).first()
    retention_days = settings.retention_days if settings else 90
    storage_path = settings.video_storage_path if settings else "/mnt/videos"
    return retention_days, storage_path


def _find_user(serial: str, db: Session) -> User | None:
    """Recherche le propriétaire d'une caméra par son numéro de série."""
    user = (
        db.query(User)
        .filter(User.camera_serials.contains([serial]), User.is_active == True)
        .first()
    )
    if not user:
        logger.warning(
            f"Numéro de série inconnu : {serial}. "
            "Aucun compte associé — onboarding requis."
        )
    return user


def _save_video_record(
    db: Session,
    file_name: str,
    file_path: str,
    file_size: int,
    camera_ts: datetime,
    user_id: int,
    retention_days: int,
) -> None:
    suffix = Path(file_name).suffix.upper().lstrip(".")
    db.add(Video(
        file_name=file_name,
        file_path=file_path,
        file_format=suffix or None,
        file_size_bytes=file_size,
        camera_timestamp=camera_ts,
        owner_id=user_id,
        matching_status="UNMATCHED",
        expires_at=datetime.utcnow() + timedelta(days=retention_days),
    ))


# ---------------------------------------------------------------------------
# Path 1 : block device (SD card / mass storage)
# ---------------------------------------------------------------------------

def _extract_insv_serial(mount_path: str) -> str | None:
    """
    Extrait le numéro de série unique depuis les métadonnées binaires d'un fichier .insv.
    Le serial Insta360 (ex: IAHEA25107V6YG) apparaît dans les 100 derniers Ko du fichier,
    juste avant le nom du modèle 'Insta360'.
    """
    for root, _, files in os.walk(mount_path):
        for file in files:
            if file.lower().endswith(".insv"):
                path = Path(root) / file
                try:
                    with open(path, "rb") as f:
                        f.seek(-100_000, 2)
                        data = f.read()
                    match = re.search(rb"([A-Z][A-Z0-9]{9,19})\x00+Insta360", data)
                    if match:
                        return match.group(1).decode("ascii")
                except Exception:
                    pass
    return None


def _find_videos(mount_path: str) -> list[Path]:
    """Parcourt le périphérique monté et retourne tous les fichiers vidéo."""
    videos = []
    for root, dirs, files in os.walk(mount_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if Path(file).suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(Path(root) / file)
    return videos


def ingest_device(device_node: str, serial: str, db: Session) -> None:
    """
    Ingestion via USB Mass Storage.
    device_node peut être :
      - un répertoire (/mnt/camera_import) : déjà monté par l'hôte via udev
      - un block device (/dev/sdb1)        : monté par nos soins dans le container
    Ordre : montage → extraction serial réel → lookup utilisateur → copie.
    """
    retention_days, storage_path = _get_settings(db)

    # Montage
    if os.path.isdir(device_node):
        mount_point = device_node
        own_mount = False
        logger.info(f"Répertoire pré-monté par l'hôte : {mount_point}")
    else:
        mount_point = tempfile.mkdtemp(prefix="camera_")
        own_mount = True
        try:
            subprocess.run(
                ["mount", "-o", "ro", device_node, mount_point],
                check=True, timeout=15,
            )
            logger.info(f"Monté : {device_node} → {mount_point}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Impossible de monter {device_node} : {e}")
            os.rmdir(mount_point)
            return

    try:
        # Extraction du serial réel depuis les métadonnées .insv (Insta360)
        # Doit précéder le lookup utilisateur car le serial USB peut être générique
        real_serial = _extract_insv_serial(mount_point)
        if real_serial:
            logger.info(f"Serial extrait des métadonnées : {real_serial} (USB : {serial})")
            serial = real_serial

        user = _find_user(serial, db)
        if not user:
            logger.warning(f"Aucun compte associé au serial {serial} — onboarding requis.")
            return

        videos = _find_videos(mount_point)
        logger.info(f"{len(videos)} vidéo(s) trouvée(s)")

        total = len(videos)
        ingested = skipped = 0
        date_str = datetime.now().strftime("%Y-%m-%d")

        for i, video_file in enumerate(videos, 1):
            dest_dir = Path(storage_path) / str(user.id) / date_str
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / video_file.name

            if dest_path.exists():
                skipped += 1
                continue

            size_mb = video_file.stat().st_size / 1_048_576
            logger.info(f"[{i}/{total}] Copie : {video_file.name} ({size_mb:.0f} Mo)")
            shutil.copy2(video_file, dest_path)
            camera_ts = datetime.fromtimestamp(os.path.getmtime(video_file))
            _save_video_record(db, video_file.name, str(dest_path),
                               video_file.stat().st_size, camera_ts,
                               user.id, retention_days)
            ingested += 1
            logger.info(f"[{i}/{total}] OK — {ingested} ingérée(s), {skipped} ignorée(s) jusqu'ici")

        db.commit()
        logger.info(
            f"Ingestion terminée — {user.first_name} {user.last_name} : "
            f"{ingested} ingérée(s), {skipped} déjà présente(s)."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Erreur ingestion block : {e}")
    finally:
        if own_mount:
            subprocess.run(["umount", mount_point], timeout=10, check=False)
            os.rmdir(mount_point)
        else:
            subprocess.run(["umount", mount_point], timeout=10, check=False)


# ---------------------------------------------------------------------------
# Path 2 : MTP/PTP (GoPro, Insta360, Sony, etc.)
# ---------------------------------------------------------------------------

def _list_mtp_videos(camera: gp.Camera, path: str = "/") -> list[tuple[str, str]]:
    """Parcourt récursivement la caméra MTP et retourne (dossier, nom) des vidéos."""
    results = []
    try:
        for name, _ in camera.folder_list_files(path):
            if Path(name).suffix.lower() in VIDEO_EXTENSIONS:
                results.append((path, name))
        for name, _ in camera.folder_list_folders(path):
            sub = path.rstrip("/") + "/" + name
            results.extend(_list_mtp_videos(camera, sub))
    except gp.GPhoto2Error as e:
        logger.debug(f"MTP list error at {path} : {e}")
    return results


def ingest_mtp_device(serial: str, db: Session) -> None:
    """
    Ingestion via MTP/PTP (gphoto2).
    Compatible avec GoPro, Insta360, Sony et la plupart des caméras modernes.
    """
    user = _find_user(serial, db)
    if not user:
        return

    retention_days, storage_path = _get_settings(db)

    # Laisser le temps au kernel de finaliser l'énumération USB
    time.sleep(2)

    camera = gp.Camera()
    try:
        camera.init()
    except gp.GPhoto2Error as e:
        logger.error(f"Impossible d'initialiser la caméra MTP ({serial}) : {e}")
        return

    try:
        video_files = _list_mtp_videos(camera)
        logger.info(f"{len(video_files)} vidéo(s) MTP trouvée(s) — {serial}")

        ingested = skipped = 0
        date_str = datetime.now().strftime("%Y-%m-%d")

        for folder, name in video_files:
            dest_dir = Path(storage_path) / str(user.id) / date_str
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / name

            if dest_path.exists():
                skipped += 1
                continue

            # Horodatage caméra depuis les métadonnées MTP
            try:
                info = camera.file_get_info(folder, name)
                camera_ts = datetime.fromtimestamp(info.file.mtime)
            except gp.GPhoto2Error:
                camera_ts = datetime.utcnow()

            camera_file = camera.file_get(folder, name, gp.GP_FILE_TYPE_NORMAL)
            camera_file.save(str(dest_path))

            file_size = dest_path.stat().st_size
            _save_video_record(db, name, str(dest_path), file_size,
                               camera_ts, user.id, retention_days)
            ingested += 1

        db.commit()
        logger.info(
            f"{user.first_name} {user.last_name} (MTP) — "
            f"{ingested} ingérée(s), {skipped} ignorée(s)."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Erreur ingestion MTP : {e}")
    finally:
        camera.exit()
