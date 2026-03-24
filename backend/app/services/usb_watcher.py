import logging
import pyudev
from app.database import SessionLocal
from app.services.video_ingestor import ingest_device, ingest_mtp_device
from app import camera_state

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Block devices (SD cards, caméras en mode Mass Storage)
# ---------------------------------------------------------------------------

def _handle_block_event(action: str, device: pyudev.Device) -> None:
    """Détecte les partitions USB montables (mass storage / carte SD)."""
    if action != "add":
        return
    if device.get("DEVTYPE") != "partition":
        return

    device_node = device.get("DEVNAME")
    serial = device.get("ID_SERIAL_SHORT") or device.get("ID_SERIAL")

    if not device_node:
        return
    if not serial:
        logger.warning(f"Périphérique block {device_node} sans numéro de série.")
        return

    logger.info(f"Block device détecté — nœud: {device_node}, série: {serial}")
    camera_state.register(serial)   # card kiosque immédiate
    _run_ingest(lambda db: ingest_device(device_node=device_node, serial=serial, db=db))


# ---------------------------------------------------------------------------
# Caméras MTP/PTP (GoPro, Insta360, Sony, etc.)
# ---------------------------------------------------------------------------

def _handle_usb_camera_event(action: str, device: pyudev.Device) -> None:
    """
    Détecte les caméras MTP/PTP à l'event 'bind' (driver attaché, device prêt).
    Filtre sur ID_GPHOTO2=1 ou ID_MTP_DEVICE=1 — udev les positionne pour
    GoPro, Insta360, Sony et la plupart des caméras modernes.
    """
    # 'bind' = driver attaché au device (plus fiable que 'add' pour gphoto2)
    if action != "bind":
        return
    if device.device_type != "usb_device":
        return

    # Garder uniquement les caméras reconnues par gphoto2 ou le stack MTP
    if not (device.get("ID_GPHOTO2") or device.get("ID_MTP_DEVICE")):
        return

    serial = device.get("ID_SERIAL_SHORT") or device.get("ID_SERIAL")
    if not serial:
        logger.warning("Caméra MTP détectée sans numéro de série — onboarding requis.")
        return

    logger.info(f"Caméra MTP/PTP détectée — série: {serial}")
    camera_state.register(serial)   # card kiosque immédiate
    _run_ingest(lambda db: ingest_mtp_device(serial=serial, db=db))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_ingest(fn) -> None:
    """Ouvre une session DB, exécute fn(db), ferme proprement."""
    db = SessionLocal()
    try:
        fn(db)
    except Exception as e:
        logger.error(f"Erreur d'ingestion : {e}")
    finally:
        db.close()


def start_usb_watcher() -> None:
    """
    Démarre deux surveillants USB en arrière-plan :
    - block  : SD cards et caméras mass storage
    - usb    : caméras MTP/PTP (GoPro, Insta360, Sony…)
    """
    context = pyudev.Context()

    monitor_block = pyudev.Monitor.from_netlink(context)
    monitor_block.filter_by(subsystem="block")
    observer_block = pyudev.MonitorObserver(monitor_block, callback=_handle_block_event)
    observer_block.daemon = True
    observer_block.start()

    monitor_usb = pyudev.Monitor.from_netlink(context)
    monitor_usb.filter_by(subsystem="usb")
    observer_usb = pyudev.MonitorObserver(monitor_usb, callback=_handle_usb_camera_event)
    observer_usb.daemon = True
    observer_usb.start()

    logger.info("Surveillant USB démarré — block devices + caméras MTP/PTP.")
