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
import requests
from sqlalchemy.orm import Session

from app.models.camera import Camera
from app.models.settings import Settings
from app.models.user import User
from app.models.video import Video
from app.services.matcher import match_videos_to_rots
from app.services.notifier import notify_videos_ready
from app import camera_state

logger = logging.getLogger(__name__)

# Extensions vidéo reconnues (insensible à la casse)
VIDEO_EXTENSIONS = {".mp4", ".mov", ".insv", ".avi", ".mts", ".lrv", ".360"}

# Taille de bloc pour la copie avec progression (4 Mo)
_COPY_CHUNK = 4 * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------------

def _get_settings(db: Session) -> tuple[int, str]:
    """Retourne (retention_days, storage_path) depuis la table settings."""
    settings = db.query(Settings).first()
    retention_days = settings.retention_days if settings else 90
    storage_path = settings.video_storage_path if settings else "/mnt/videos"
    return retention_days, storage_path


def _parse_model_string(model_str: str | None) -> tuple[str | None, str | None]:
    """Sépare 'GoPro HERO12 Black' en ('GoPro', 'HERO12 Black')."""
    if not model_str:
        return None, None
    for make in ("GoPro", "Insta360", "Sony", "DJI", "Garmin", "Olympus"):
        if model_str.startswith(make):
            model = model_str[len(make):].strip() or None
            return make, model
    return None, model_str


def _upsert_camera(
    db: Session,
    serial: str,
    make: str | None = None,
    model: str | None = None,
    usb_serial: str | None = None,
    vendor_id: str | None = None,
) -> None:
    """Crée ou met à jour l'enregistrement d'une caméra dans la table cameras."""
    cam = db.query(Camera).filter(Camera.serial == serial).first()
    if cam:
        if make:       cam.make       = make
        if model:      cam.model      = model
        if usb_serial: cam.usb_serial = usb_serial
        if vendor_id:  cam.vendor_id  = vendor_id
        cam.updated_at = datetime.utcnow()
    else:
        db.add(Camera(serial=serial, make=make, model=model,
                      usb_serial=usb_serial, vendor_id=vendor_id))


def _find_user(serial: str, db: Session, usb_serial: str | None = None) -> User | None:
    """
    Recherche le propriétaire d'une caméra par son numéro de série.
    Si le vrai serial (extrait des métadonnées) ne trouve rien, retente avec le
    serial USB brut (cas Insta360 "0001"), et met à jour camera_serials si trouvé.
    """
    user = (
        db.query(User)
        .filter(User.camera_serials.contains([serial]), User.is_active == True)
        .first()
    )
    if user:
        return user

    # Fallback : serial USB brut (ex. "0001" pour Insta360 Mass Storage)
    if usb_serial and usb_serial != serial:
        user = (
            db.query(User)
            .filter(User.camera_serials.contains([usb_serial]), User.is_active == True)
            .first()
        )
        if user:
            # Remplacer l'USB serial générique par le vrai serial dans le compte
            user.camera_serials = [serial if s == usb_serial else s for s in user.camera_serials]
            db.flush()
            logger.info(f"Serial mis à jour : {usb_serial} → {serial} (user id={user.id})")
            return user

    logger.warning(
        f"Numéro de série inconnu : {serial}. "
        "Aucun compte associé — onboarding requis."
    )
    return None


def _generate_thumbnail(video_path: str) -> str | None:
    """
    Extrait une frame à t=5s avec ffmpeg et la sauvegarde en JPEG à côté de la vidéo.
    Retourne le chemin de la vignette, ou None en cas d'échec.
    """
    thumb_path = str(Path(video_path).with_suffix(".jpg"))
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", "5",
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "3",
                "-vf", "scale=480:-1",
                thumb_path,
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and Path(thumb_path).exists():
            return thumb_path
        logger.warning(f"[THUMB] ffmpeg a échoué pour {video_path}: {result.stderr[-200:]}")
    except Exception as e:
        logger.warning(f"[THUMB] Erreur génération vignette {video_path}: {e}")
    return None


def _save_video_record(
    db: Session,
    file_name: str,
    file_path: str,
    file_size: int,
    camera_ts: datetime,
    user_id: int,
    retention_days: int,
    rot_id: int | None = None,
    group_id: int | None = None,
) -> None:
    suffix = Path(file_name).suffix.upper().lstrip(".")
    thumbnail_path = _generate_thumbnail(file_path)
    db.add(Video(
        file_name=file_name,
        file_path=file_path,
        file_format=suffix or None,
        file_size_bytes=file_size,
        camera_timestamp=camera_ts,
        owner_id=user_id,
        rot_id=rot_id,
        group_id=group_id,
        matching_status="MATCHED" if rot_id else "UNMATCHED",
        thumbnail_path=thumbnail_path,
        expires_at=datetime.utcnow() + timedelta(days=retention_days),
    ))


def _copy_with_progress(src: Path, dest: Path, serial: str) -> None:
    """Copie src → dest par blocs de 4 Mo en mettant à jour camera_state."""
    with open(src, "rb") as fin, open(dest, "wb") as fout:
        while True:
            chunk = fin.read(_COPY_CHUNK)
            if not chunk:
                break
            fout.write(chunk)
            camera_state.add_bytes(serial, len(chunk))


# ---------------------------------------------------------------------------
# Path 1 : block device (SD card / mass storage)
# ---------------------------------------------------------------------------

def _extract_insv_camera_info(mount_path: str) -> tuple[str | None, str | None, str | None]:
    """
    Extrait (serial, make, model) depuis les métadonnées binaires d'un fichier .insv.
    - serial : ex "IAHEA25107V6YG" (50 octets avant la chaîne 'Insta360')
    - make   : "Insta360"
    - model  : ex "X5", "X4", "ONE RS"… (octets après 'Insta360')
    """
    for root, _, files in os.walk(mount_path):
        for file in files:
            if file.lower().endswith(".insv"):
                path = Path(root) / file
                try:
                    with open(path, "rb") as f:
                        f.seek(-100_000, 2)
                        data = f.read()
                    pos = data.find(b"Insta360")
                    if pos > 10:
                        # Serial : dans les 50 octets qui précèdent "Insta360"
                        prefix = data[max(0, pos - 50): pos]
                        serial_match = re.search(rb"([A-Z][A-Z0-9]{9,19})", prefix)
                        serial = serial_match.group(1).decode("ascii") if serial_match else None

                        # Modèle : juste après "Insta360" (ex: " X5\x00" ou " ONE RS\x00")
                        suffix = data[pos + 8: pos + 32]
                        model_match = re.search(rb"\s+([A-Z0-9][A-Z0-9 ]{1,14}?)(?:\x00|[\x80-\xff])", suffix)
                        model = model_match.group(1).decode("ascii").strip() if model_match else None

                        logger.info(f"[INSV] serial={serial}, model={model}")
                        return serial, "Insta360", model
                    logger.warning(f"'Insta360' non trouvé dans {file}")
                except Exception as e:
                    logger.warning(f"Erreur lecture métadonnées {file} : {e}")
    return None, None, None


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
    # serial USB brut (clé de la session kiosque enregistrée dans usb_watcher)
    usb_serial = serial

    camera_state.update(usb_serial, status="DETECTING")
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
            camera_state.update(usb_serial, status="ERROR", error_msg=str(e),
                                 finished_at=time.time())
            return

    try:
        # Extraction du serial réel + make/model depuis les métadonnées .insv (Insta360)
        insv_serial, insv_make, insv_model = _extract_insv_camera_info(mount_point)
        if insv_serial:
            logger.info(f"[INGEST][Block] Serial corrigé depuis métadonnées .insv : {insv_serial} (USB brut : {usb_serial})")
            serial = insv_serial

        user = _find_user(serial, db, usb_serial=usb_serial)
        if not user:
            camera_state.update(usb_serial, status="UNKNOWN", finished_at=time.time())
            return

        camera_state.update(usb_serial, owner_name=f"{user.first_name} {user.last_name}")

        # Enregistrer / mettre à jour les métadonnées de la caméra
        make = insv_make
        model = insv_model
        _upsert_camera(db, serial, make=make, model=model, usb_serial=usb_serial)
        if make or model:
            camera_state.update(usb_serial, make=make or "", model=model or "")

        logger.info(f"[INGEST][Block] ━━━ Début ingestion — {user.first_name} {user.last_name} | serial: {serial} ━━━")
        video_files = _find_videos(mount_point)
        logger.info(f"[INGEST][Block] {len(video_files)} vidéo(s) trouvée(s) sur le périphérique")

        camera_state.update(usb_serial, video_total=len(video_files))

        # Matching avant téléchargement : [(filename, cre_ts), ...]
        video_list = [
            (v.name, int(os.path.getmtime(v)))
            for v in video_files
        ]
        matches = match_videos_to_rots(video_list, user.id, db)

        # Labels des rotations matchées pour le kiosque
        preview_rot_ids = sorted({m[0] for m in matches.values() if m})
        camera_state.update(usb_serial, rot_labels=[f"Rot #{r}" for r in preview_rot_ids])

        total = len(video_files)
        ingested = skipped = unmatched = 0
        date_str = datetime.now().strftime("%Y-%m-%d")
        matched_rot_ids: list[int] = []

        for i, video_file in enumerate(video_files, 1):
            match = matches.get(video_file.name)
            if not match:
                unmatched += 1
                logger.info(f"[INGEST][Block] [{i}/{total}] Ignoré — aucun rot correspondant : {video_file.name}")
                continue

            rot_id, group_id = match
            dest_dir = Path(storage_path) / str(user.id) / date_str
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / video_file.name

            if dest_path.exists():
                skipped += 1
                logger.info(f"[INGEST][Block] [{i}/{total}] Ignoré — déjà présent : {video_file.name}")
                continue

            size = video_file.stat().st_size
            size_mb = size / 1_048_576
            logger.info(f"[INGEST][Block] [{i}/{total}] Copie : {video_file.name} ({size_mb:.0f} Mo) → rot #{rot_id}")

            camera_state.update(usb_serial, status="COPYING", video_index=i,
                                 bytes_done=0, bytes_total=size, speed_bps=0)

            _copy_with_progress(video_file, dest_path, usb_serial)

            camera_ts = datetime.fromtimestamp(os.path.getmtime(video_file))
            _save_video_record(db, video_file.name, str(dest_path),
                               video_file.stat().st_size, camera_ts,
                               user.id, retention_days, rot_id, group_id)
            matched_rot_ids.append(rot_id)
            ingested += 1
            logger.info(f"[INGEST][Block] [{i}/{total}] ✔ Copiée avec succès")

        db.commit()
        camera_state.update(usb_serial, status="DONE", finished_at=time.time())
        logger.info(
            f"[INGEST][Block] ━━━ Fin ingestion — {user.first_name} {user.last_name} : "
            f"{ingested} copiée(s), {skipped} déjà présente(s), {unmatched} sans rot ━━━"
        )
        if matched_rot_ids:
            notify_videos_ready(user, list(set(matched_rot_ids)), db)

    except Exception as e:
        db.rollback()
        camera_state.update(usb_serial, status="ERROR", error_msg=str(e),
                             finished_at=time.time())
        logger.error(f"Erreur ingestion block : {e}")
    finally:
        if own_mount:
            subprocess.run(["umount", mount_point], timeout=10, check=False)
            os.rmdir(mount_point)
        else:
            subprocess.run(["umount", mount_point], timeout=10, check=False)


# ---------------------------------------------------------------------------
# Path 2 : GoPro via HTTP (Open GoPro API — USB NCM)
# ---------------------------------------------------------------------------

GOPRO_BASE_URL = "http://172.26.166.51:8080"
GOPRO_MEDIA_LIST = f"{GOPRO_BASE_URL}/gopro/media/list"
GOPRO_DOWNLOAD_BASE = f"{GOPRO_BASE_URL}/videos/DCIM"


def ingest_gopro_http(serial: str, db: Session) -> None:
    """
    Ingestion GoPro via Open GoPro HTTP API (interface USB NCM).
    Télécharge tous les fichiers vidéo présents sur la caméra.
    """
    camera_state.update(serial, status="DETECTING")

    user = _find_user(serial, db)
    if not user:
        camera_state.update(serial, status="UNKNOWN", finished_at=time.time())
        return

    camera_state.update(serial, owner_name=f"{user.first_name} {user.last_name}")

    logger.info(f"[INGEST][GoPro] ━━━ Début ingestion — {user.first_name} {user.last_name} | serial: {serial} ━━━")
    retention_days, storage_path = _get_settings(db)

    # Laisser le temps à l'interface USB NCM d'être configurée
    logger.info("[INGEST][GoPro] Attente interface USB NCM (5s)...")

    time.sleep(5)

    # Activer le wired USB control mode (requis sur HERO11 pour accéder aux médias)
    try:
        r = requests.get(f"{GOPRO_BASE_URL}/gopro/camera/control/wired_usb?p=1", timeout=10)
        logger.info(f"[INGEST][GoPro] Wired USB control activé : HTTP {r.status_code}")
    except requests.RequestException as e:
        logger.warning(f"[INGEST][GoPro] Wired USB control — erreur (non bloquant) : {e}")

    time.sleep(2)

    # Récupérer le modèle GoPro via l'API info
    try:
        info_resp = requests.get(f"{GOPRO_BASE_URL}/gopro/camera/info", timeout=10)
        if info_resp.ok:
            info_data = info_resp.json()
            gopro_model = info_data.get("info", {}).get("model_name") or info_data.get("model_name")
            make, model = _parse_model_string(gopro_model)
            if not make:
                make = "GoPro"
            _upsert_camera(db, serial, make=make, model=model, vendor_id="2672")
            camera_state.update(serial, make=make, model=model or "")
            logger.info(f"[INGEST][GoPro] Caméra : {make} {model or ''} | serial: {serial}")
    except requests.RequestException as e:
        logger.warning(f"[INGEST][GoPro] Impossible de récupérer le modèle caméra : {e}")
        _upsert_camera(db, serial, make="GoPro", vendor_id="2672")
        camera_state.update(serial, make="GoPro")

    # La GoPro peut retourner une liste vide si le serveur média n'est pas encore prêt
    # → on retente jusqu'à 5 fois avec 5s d'intervalle
    media_data = None
    for attempt in range(1, 6):
        try:
            resp = requests.get(GOPRO_MEDIA_LIST, timeout=10)
            resp.raise_for_status()
            media_data = resp.json()
            if media_data.get("media"):
                logger.info(f"[INGEST][GoPro] Media list obtenue (tentative {attempt}/5)")
                break
            logger.info(f"[INGEST][GoPro] Media list vide — nouvel essai dans 5s ({attempt}/5)")
            time.sleep(5)
        except requests.RequestException as e:
            logger.warning(f"[INGEST][GoPro] Tentative {attempt}/5 échouée : {e}")
            time.sleep(5)

    if not media_data:
        logger.error("[INGEST][GoPro] Aucune réponse après 5 tentatives — ingestion abandonnée")
        camera_state.update(serial, status="ERROR",
                             error_msg="Aucune réponse GoPro après 5 tentatives",
                             finished_at=time.time())
        return

    # Format: {"id": "...", "media": [{"d": "100GOPRO", "fs": [{"n": "GX010488.MP4", "s": "...", "cre": timestamp}]}]}
    all_files: list[tuple[str, str, int, int]] = []  # (dossier, nom, taille, cre)
    for entry in media_data.get("media", []):
        folder = entry.get("d", "")
        for f in entry.get("fs", []):
            name = f.get("n", "")
            if Path(name).suffix.lower() in VIDEO_EXTENSIONS:
                size = int(f.get("s", 0))
                cre = int(f.get("cre", 0))
                all_files.append((folder, name, size, cre))

    if not all_files:
        logger.info(f"[INGEST][GoPro] Aucune vidéo trouvée sur la carte SD")
        camera_state.update(serial, status="DONE", finished_at=time.time())
        return

    logger.info(f"[INGEST][GoPro] {len(all_files)} vidéo(s) présente(s) sur la carte SD")
    camera_state.update(serial, video_total=len(all_files))

    # Matching avant téléchargement
    video_list = [(name, cre) for _, name, _, cre in all_files]
    matches = match_videos_to_rots(video_list, user.id, db)

    # Labels des rotations matchées pour le kiosque
    preview_rot_ids = sorted({m[0] for m in matches.values()})
    camera_state.update(serial, rot_labels=[f"Rot #{r}" for r in preview_rot_ids])

    # Index par nom pour accès rapide aux métadonnées
    file_meta = {name: (folder, size, cre) for folder, name, size, cre in all_files}

    ingested = skipped = unmatched = 0
    total = len(all_files)
    date_str = datetime.now().strftime("%Y-%m-%d")
    matched_rot_ids: list[int] = []

    for i, (name, cre) in enumerate(video_list, 1):
        match = matches.get(name)
        if not match:
            unmatched += 1
            logger.info(f"[INGEST][GoPro] [{i}/{total}] Ignoré — aucun rot correspondant : {name}")
            continue

        rot_id, group_id = match
        folder, size, cre = file_meta[name]
        dest_dir = Path(storage_path) / str(user.id) / date_str
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / name

        if dest_path.exists():
            skipped += 1
            logger.info(f"[INGEST][GoPro] [{i}/{total}] Ignoré — déjà présent : {name}")
            continue

        url = f"{GOPRO_DOWNLOAD_BASE}/{folder}/{name}"
        size_mb = size / 1_048_576
        logger.info(f"[INGEST][GoPro] [{i}/{total}] Téléchargement : {name} ({size_mb:.0f} Mo) → rot #{rot_id}")

        camera_state.update(serial, status="DOWNLOADING", video_index=i,
                             bytes_done=0, bytes_total=size, speed_bps=0)

        try:
            with requests.get(url, stream=True, timeout=300) as dl:
                dl.raise_for_status()
                with open(dest_path, "wb") as out:
                    for chunk in dl.iter_content(chunk_size=1 * 1024 * 1024):
                        out.write(chunk)
                        camera_state.add_bytes(serial, len(chunk))
        except requests.RequestException as e:
            logger.error(f"[INGEST][GoPro] [{i}/{total}] Échec téléchargement {name} : {e}")
            dest_path.unlink(missing_ok=True)
            continue

        camera_ts = datetime.fromtimestamp(cre) if cre else datetime.utcnow()
        actual_size = dest_path.stat().st_size
        _save_video_record(db, name, str(dest_path), actual_size,
                           camera_ts, user.id, retention_days, rot_id, group_id)
        matched_rot_ids.append(rot_id)
        ingested += 1
        logger.info(f"[INGEST][GoPro] [{i}/{total}] ✔ Téléchargée avec succès")

    db.commit()
    camera_state.update(serial, status="DONE", finished_at=time.time())
    logger.info(
        f"[INGEST][GoPro] ━━━ Fin ingestion — {user.first_name} {user.last_name} : "
        f"{ingested} téléchargée(s), {skipped} déjà présente(s), {unmatched} sans rot ━━━"
    )
    if matched_rot_ids:
        notify_videos_ready(user, list(set(matched_rot_ids)), db)


# ---------------------------------------------------------------------------
# Path 3 : MTP/PTP (Insta360, Sony, etc.)
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
    camera_state.update(serial, status="DETECTING")

    user = _find_user(serial, db)
    if not user:
        camera_state.update(serial, status="UNKNOWN", finished_at=time.time())
        return

    camera_state.update(serial, owner_name=f"{user.first_name} {user.last_name}")

    retention_days, storage_path = _get_settings(db)

    # Laisser le temps au kernel de finaliser l'énumération USB
    time.sleep(2)

    camera = gp.Camera()
    try:
        camera.init()
    except gp.GPhoto2Error as e:
        logger.error(f"Impossible d'initialiser la caméra MTP ({serial}) : {e}")
        camera_state.update(serial, status="ERROR", error_msg=str(e),
                             finished_at=time.time())
        return

    try:
        # Récupérer make/model depuis gphoto2
        try:
            abilities = camera.get_abilities()
            make, model = _parse_model_string(abilities.model)
            _upsert_camera(db, serial, make=make, model=model)
            camera_state.update(serial, make=make or "", model=model or "")
            logger.info(f"[INGEST][MTP] Caméra : {make or ''} {model or ''} | serial: {serial}")
        except Exception as e:
            logger.warning(f"[INGEST][MTP] Impossible de lire les abilities caméra : {e}")

        logger.info(f"[INGEST][MTP] ━━━ Début ingestion — {user.first_name} {user.last_name} | serial: {serial} ━━━")
        video_files = _list_mtp_videos(camera)
        logger.info(f"[INGEST][MTP] {len(video_files)} vidéo(s) trouvée(s) sur la caméra")

        camera_state.update(serial, video_total=len(video_files))

        # Récupérer les horodatages et tailles pour le matching (sans télécharger)
        timestamps: dict[str, int] = {}
        file_sizes: dict[str, int] = {}
        for folder, name in video_files:
            try:
                info = camera.file_get_info(folder, name)
                timestamps[name] = int(info.file.mtime)
                file_sizes[name] = int(info.file.size)
            except gp.GPhoto2Error:
                timestamps[name] = int(datetime.utcnow().timestamp())
                file_sizes[name] = 0

        # Matching avant téléchargement
        video_list = [(name, timestamps[name]) for _, name in video_files]
        matches = match_videos_to_rots(video_list, user.id, db)

        # Labels des rotations matchées pour le kiosque
        preview_rot_ids = sorted({m[0] for m in matches.values() if m})
        camera_state.update(serial, rot_labels=[f"Rot #{r}" for r in preview_rot_ids])

        ingested = skipped = unmatched = 0
        total = len(video_files)
        date_str = datetime.now().strftime("%Y-%m-%d")
        matched_rot_ids: list[int] = []

        for i, (folder, name) in enumerate(video_files, 1):
            match = matches.get(name)
            if not match:
                unmatched += 1
                logger.info(f"[INGEST][MTP] [{i}/{total}] Ignoré — aucun rot correspondant : {name}")
                continue

            rot_id, group_id = match
            dest_dir = Path(storage_path) / str(user.id) / date_str
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / name

            if dest_path.exists():
                skipped += 1
                logger.info(f"[INGEST][MTP] [{i}/{total}] Ignoré — déjà présent : {name}")
                continue

            file_size = file_sizes.get(name, 0)
            camera_state.update(serial, status="COPYING", video_index=i,
                                 bytes_done=0, bytes_total=file_size, speed_bps=0)

            camera_ts = datetime.fromtimestamp(timestamps[name])
            logger.info(f"[INGEST][MTP] [{i}/{total}] Téléchargement : {name} → rot #{rot_id}")
            camera_file = camera.file_get(folder, name, gp.GP_FILE_TYPE_NORMAL)
            camera_file.save(str(dest_path))

            actual_size = dest_path.stat().st_size
            # Signaler les bytes d'un coup (gphoto2 ne donne pas de chunks)
            camera_state.add_bytes(serial, actual_size)

            _save_video_record(db, name, str(dest_path), actual_size,
                               camera_ts, user.id, retention_days, rot_id, group_id)
            matched_rot_ids.append(rot_id)
            ingested += 1
            logger.info(f"[INGEST][MTP] [{i}/{total}] ✔ Téléchargée avec succès")

        db.commit()
        camera_state.update(serial, status="DONE", finished_at=time.time())
        logger.info(
            f"[INGEST][MTP] ━━━ Fin ingestion — {user.first_name} {user.last_name} : "
            f"{ingested} téléchargée(s), {skipped} déjà présente(s), {unmatched} sans rot ━━━"
        )
        if matched_rot_ids:
            notify_videos_ready(user, list(set(matched_rot_ids)), db)

    except Exception as e:
        db.rollback()
        camera_state.update(serial, status="ERROR", error_msg=str(e),
                             finished_at=time.time())
        logger.error(f"Erreur ingestion MTP : {e}")
    finally:
        camera.exit()
