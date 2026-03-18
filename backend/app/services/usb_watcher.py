import logging
import pyudev
from app.database import SessionLocal
from app.services.video_ingestor import ingest_device, ingest_mtp_device

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
    _run_ingest(lambda db: ingest_device(device_node=device_node, serial=serial, db=db))


# ---------------------------------------------------------------------------
# Caméras MTP/PTP (GoPro, Insta360, Sony, etc.)
# ---------------------------------------------------------------------------

def _handle_usb_camera_event(action: str, device: pyudev.Device) -> None:
    """
    Détecte les interfaces USB de classe Imaging (bInterfaceClass=06 = PTP/MTP).
    Chaque caméra expose une telle interface quand elle se connecte en mode photo.
    """
    if action != "add":
        return
    if device.device_type != "usb_interface":
        return

    # Vérifier la classe d'interface USB : 06 = Imaging (PTP/MTP)
    raw = device.attributes.get("bInterfaceClass", b"")
    iface_class = (raw.decode("ascii", errors="ignore") if isinstance(raw, bytes) else str(raw)).strip()
    if iface_class != "06":
        return

    # Remonter au device USB parent pour lire le numéro de série
    parent = device.find_parent("usb", "usb_device")
    if parent is None:
        return

    serial = parent.get("ID_SERIAL_SHORT") or parent.get("ID_SERIAL")
    if not serial:
        logger.warning("Caméra MTP détectée sans numéro de série — onboarding requis.")
        return

    logger.info(f"Caméra MTP/PTP détectée — série: {serial}")
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
