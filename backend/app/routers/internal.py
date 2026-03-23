import logging
import os
import tempfile
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel

from app.database import SessionLocal, get_db
from app.models.user import User
from app.services.video_ingestor import ingest_device, ingest_gopro_http, ingest_mtp_device
from fastapi import Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/internal", tags=["Interne"])
logger = logging.getLogger(__name__)

# Liste des caméras inconnues en attente d'onboarding
# Chaque entrée : {serial, mtp, vendor_id, device_node, model_name, connected_at}
_cameras: list[dict] = []


def get_pending_cameras() -> list[dict]:
    return list(_cameras)


def remove_pending_camera(serial: str) -> None:
    _cameras[:] = [c for c in _cameras if c["serial"] != serial]


def clear_pending_cameras() -> None:
    _cameras.clear()


# Compatibilité avec le code existant (onboard dans users.py)
def get_pending_onboarding() -> dict | None:
    return _cameras[0] if _cameras else None


def clear_pending_onboarding() -> None:
    clear_pending_cameras()


def _vendor_display(vendor_id: str | None, model_name: str | None) -> str:
    if model_name:
        return model_name
    if vendor_id == "2672":
        return "GoPro"
    return "Caméra USB"


class CameraEvent(BaseModel):
    serial:      str
    device_node: str | None = None
    mtp:         bool = False
    vendor_id:   str | None = None
    model_name:  str | None = None  # ex: "GoPro HERO12 Black" (optionnel, fourni par le script hôte)


def _run_in_background(target, **kwargs):
    def worker():
        db = SessionLocal()
        try:
            target(**kwargs, db=db)
        finally:
            db.close()
    threading.Thread(target=worker, daemon=True).start()


@router.post("/camera-connected")
def camera_connected(event: CameraEvent):
    """
    Appelé par la règle udev de l'hôte quand une caméra est branchée.
    Si le serial est inconnu → ajouté à la liste d'onboarding.
    Si connu → déclenche l'ingestion en arrière-plan.
    """
    logger.info(
        f"[USB] Caméra branchée — serial: {event.serial} | "
        f"mtp: {event.mtp} | vendor_id: {repr(event.vendor_id)} | "
        f"device_node: {event.device_node} | model: {event.model_name}"
    )

    from app.models.camera import Camera
    from app.services.video_ingestor import _parse_model_string, _upsert_camera

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.camera_serials.contains([event.serial]),
            User.is_active == True,
        ).first()

        # Persister les métadonnées connues au moment de la connexion
        if event.model_name or event.vendor_id:
            make, model = _parse_model_string(event.model_name)
            if not make and event.vendor_id == "2672":
                make = "GoPro"
            _upsert_camera(db, event.serial, make=make, model=model, vendor_id=event.vendor_id)
            db.commit()

        # Enrichir le model_name depuis la table cameras
        cam_record = db.query(Camera).filter(Camera.serial == event.serial).first()
        if cam_record and (cam_record.make or cam_record.model):
            enriched_model = " ".join(filter(None, [cam_record.make, cam_record.model]))
        else:
            enriched_model = _vendor_display(event.vendor_id, event.model_name)

        # Capturer le nom avant fermeture de session (évite DetachedInstanceError)
        user_name = f"{user.first_name} {user.last_name}" if user else None
    finally:
        db.close()

    if not user:
        logger.info(f"[USB] Serial inconnu : {event.serial} — onboarding requis")
        # Éviter les doublons
        if not any(c["serial"] == event.serial for c in _cameras):
            _cameras.append({
                "serial":      event.serial,
                "mtp":         event.mtp,
                "vendor_id":   event.vendor_id,
                "device_node": event.device_node,
                "model_name":  enriched_model,
                "connected_at": datetime.now(timezone.utc).isoformat(),
            })
        return {"status": "onboarding_required", "serial": event.serial}

    # Serial connu → ingestion
    if event.mtp and event.vendor_id == "2672":
        logger.info(f"[USB] → GoPro HERO ({user_name}) — Open GoPro HTTP")
        _run_in_background(ingest_gopro_http, serial=event.serial)
    elif event.mtp:
        logger.info(f"[USB] → MTP/PTP ({user_name}) — gphoto2")
        _run_in_background(ingest_mtp_device, serial=event.serial)
    elif event.device_node:
        logger.info(f"[USB] → Mass Storage ({user_name}) — {event.device_node}")
        _run_in_background(ingest_device, device_node=event.device_node, serial=event.serial)
    else:
        logger.warning(f"[USB] Événement ignoré — ni device_node ni mtp=True (serial: {event.serial})")

    return {"status": "ingestion_started"}


@router.get("/onboarding/pending")
def onboarding_pending():
    """
    Retourne la liste des caméras inconnues en attente d'onboarding.
    Réponse : {"cameras": [{serial, model_name, connected_at, ...}, ...]}
    """
    return {"cameras": get_pending_cameras()}


@router.delete("/onboarding/pending", status_code=204)
def onboarding_clear(serial: str | None = Query(default=None)):
    """
    Efface une caméra spécifique de la liste (serial=XXX) ou toute la liste.
    """
    if serial:
        remove_pending_camera(serial)
    else:
        clear_pending_cameras()


@router.post("/rots/upload-pdf", status_code=201)
def internal_upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Endpoint interne pour l'ingestion de PDFs Afifly depuis n8n (sans authentification).
    Accessible uniquement depuis le réseau Docker interne.
    """
    from app.services.pdf_parser import parse_afifly_pdf
    from app.services.rot_service import upsert_rot

    if not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "detail": "Fichier non PDF ignoré.", "file": file.filename}

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        data = parse_afifly_pdf(tmp_path)
    except Exception as e:
        os.unlink(tmp_path)
        logger.warning(f"[PDF] Erreur parsing {file.filename}: {e}")
        return {"status": "error", "detail": str(e), "file": file.filename}

    try:
        rot = upsert_rot(data, db, source_pdf_path=tmp_path)
        logger.info(f"[PDF] Importé : rot n°{rot.rot_number} ({file.filename})")
        return {"status": "ok", "rot_id": rot.id, "rot_number": rot.rot_number, "file": file.filename}
    except Exception as e:
        logger.warning(f"[PDF] Erreur persistance {file.filename}: {e}")
        return {"status": "error", "detail": str(e), "file": file.filename}
