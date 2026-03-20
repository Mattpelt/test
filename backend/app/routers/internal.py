import logging
import threading
from fastapi import APIRouter
from pydantic import BaseModel

from app.database import SessionLocal
from app.services.video_ingestor import ingest_device, ingest_gopro_http, ingest_mtp_device

router = APIRouter(prefix="/internal", tags=["Interne"])

logger = logging.getLogger(__name__)


class CameraEvent(BaseModel):
    serial: str
    device_node: str | None = None   # présent pour les block devices (SD cards)
    mtp: bool = False                # True = caméra MTP/PTP, False = block device
    vendor_id: str | None = None


def _run_in_background(target, **kwargs):
    """Lance l'ingestion dans un thread séparé avec sa propre session DB."""
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
    Déclenche l'ingestion en arrière-plan (non bloquant).
    """
    logger.info(f"Événement caméra reçu — serial: {event.serial}, mtp: {event.mtp}, vendor_id: {repr(event.vendor_id)}")

    if event.mtp and event.vendor_id == "2672":
        # GoPro — ingestion via Open GoPro HTTP API (USB NCM)
        _run_in_background(ingest_gopro_http, serial=event.serial)
    elif event.mtp:
        # Autres caméras MTP (Sony, etc.)
        _run_in_background(ingest_mtp_device, serial=event.serial)
    elif event.device_node:
        # USB Mass Storage (Insta360 X5, SD card, etc.)
        _run_in_background(ingest_device, device_node=event.device_node, serial=event.serial)
    else:
        logger.warning("Événement caméra reçu sans device_node ni mtp=True — ignoré.")

    return {"status": "ingestion démarrée"}
