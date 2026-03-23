import logging
import threading
from fastapi import APIRouter
from pydantic import BaseModel

from app.database import SessionLocal
from app.models.user import User
from app.services.video_ingestor import ingest_device, ingest_gopro_http, ingest_mtp_device

router = APIRouter(prefix="/internal", tags=["Interne"])
logger = logging.getLogger(__name__)

# État partagé : caméra en attente d'onboarding (serial inconnu)
_pending: dict = {"serial": None, "mtp": False, "vendor_id": None, "device_node": None}


def get_pending_onboarding() -> dict | None:
    return dict(_pending) if _pending["serial"] else None


def clear_pending_onboarding() -> None:
    _pending.update({"serial": None, "mtp": False, "vendor_id": None, "device_node": None})


class CameraEvent(BaseModel):
    serial: str
    device_node: str | None = None
    mtp: bool = False
    vendor_id: str | None = None


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
    Si le serial est inconnu → met en attente d'onboarding.
    Si connu → déclenche l'ingestion en arrière-plan.
    """
    logger.info(
        f"[USB] Caméra branchée — serial: {event.serial} | "
        f"mtp: {event.mtp} | vendor_id: {repr(event.vendor_id)} | "
        f"device_node: {event.device_node}"
    )

    # Vérifier si le serial est connu
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.camera_serials.contains([event.serial]),
            User.is_active == True,
        ).first()
    finally:
        db.close()

    if not user:
        logger.info(f"[USB] Serial inconnu : {event.serial} — onboarding requis")
        _pending.update({
            "serial": event.serial,
            "mtp": event.mtp,
            "vendor_id": event.vendor_id,
            "device_node": event.device_node,
        })
        return {"status": "onboarding_required", "serial": event.serial}

    # Serial connu → ingestion
    if event.mtp and event.vendor_id == "2672":
        logger.info(f"[USB] → GoPro HERO ({user.first_name} {user.last_name}) — Open GoPro HTTP")
        _run_in_background(ingest_gopro_http, serial=event.serial)
    elif event.mtp:
        logger.info(f"[USB] → MTP/PTP ({user.first_name} {user.last_name}) — gphoto2")
        _run_in_background(ingest_mtp_device, serial=event.serial)
    elif event.device_node:
        logger.info(f"[USB] → Mass Storage ({user.first_name} {user.last_name}) — {event.device_node}")
        _run_in_background(ingest_device, device_node=event.device_node, serial=event.serial)
    else:
        logger.warning(f"[USB] Événement ignoré — ni device_node ni mtp=True (serial: {event.serial})")

    return {"status": "ingestion_started"}


@router.get("/onboarding/pending")
def onboarding_pending():
    """Retourne le serial en attente d'onboarding, ou null si aucun."""
    pending = get_pending_onboarding()
    return pending if pending else {"serial": None}


@router.delete("/onboarding/pending", status_code=204)
def onboarding_clear():
    """Efface l'état d'onboarding en attente."""
    clear_pending_onboarding()
