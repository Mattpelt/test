import logging
import pyudev
from app.database import SessionLocal
from app.services.video_ingestor import ingest_device

logger = logging.getLogger(__name__)


def _handle_event(action: str, device: pyudev.Device) -> None:
    """
    Appelé par pyudev à chaque événement USB.
    On ne traite que les partitions qui viennent d'être branchées.
    """
    if action != "add":
        return

    # On s'intéresse uniquement aux partitions (ex: /dev/sdb1), pas aux disques bruts
    if device.get("DEVTYPE") != "partition":
        return

    device_node = device.get("DEVNAME")          # ex: /dev/sdb1
    serial = (
        device.get("ID_SERIAL_SHORT")            # numéro de série court (privilégié)
        or device.get("ID_SERIAL")               # numéro de série long (repli)
    )

    if not device_node:
        logger.warning("Périphérique détecté sans DEVNAME, ignoré.")
        return

    if not serial:
        logger.warning(f"Périphérique {device_node} détecté sans numéro de série.")
        # TODO : déclencher le flux d'onboarding manuel (F02)
        return

    logger.info(f"Caméra détectée — nœud: {device_node}, série: {serial}")

    # Ouvrir une session base de données dédiée à cet événement
    db = SessionLocal()
    try:
        ingest_device(device_node=device_node, serial=serial, db=db)
    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion de {device_node}: {e}")
    finally:
        db.close()


def start_usb_watcher() -> None:
    """
    Démarre le surveillant USB en arrière-plan.
    Écoute les événements noyau via netlink (fonctionne en conteneur privilégié).
    """
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="block")

    observer = pyudev.MonitorObserver(monitor, callback=_handle_event)
    observer.daemon = True   # s'arrête automatiquement avec le processus principal
    observer.start()

    logger.info("Surveillant USB démarré — en attente de branchement caméra.")
