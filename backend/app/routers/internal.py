import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.video_ingestor import ingest_device, ingest_mtp_device

router = APIRouter(prefix="/internal", tags=["Interne"])

logger = logging.getLogger(__name__)


class CameraEvent(BaseModel):
    serial: str
    device_node: str | None = None   # présent pour les block devices (SD cards)
    mtp: bool = False                # True = caméra MTP/PTP, False = block device


@router.post("/camera-connected")
def camera_connected(event: CameraEvent, db: Session = Depends(get_db)):
    """
    Appelé par la règle udev de l'hôte quand une caméra est branchée.
    Déclenche l'ingestion MTP ou block selon le type de device.
    """
    logger.info(f"Événement caméra reçu — serial: {event.serial}, mtp: {event.mtp}")

    if event.mtp:
        ingest_mtp_device(serial=event.serial, db=db)
    elif event.device_node:
        ingest_device(device_node=event.device_node, serial=event.serial, db=db)
    else:
        logger.warning("Événement caméra reçu sans device_node ni mtp=True — ignoré.")

    return {"status": "ok"}
