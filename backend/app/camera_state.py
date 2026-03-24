"""
Store en mémoire partagé — état temps réel de chaque caméra en cours d'ingestion.
Thread-safe. Chaque session est auto-nettoyée 5 min après DONE/ERROR/UNKNOWN.
"""
import threading
import time

_CLEANUP_AFTER = 300   # secondes après DONE/ERROR/UNKNOWN
_SPEED_WINDOW  = 5.0   # fenêtre glissante pour le calcul de vitesse (secondes)

_lock     = threading.Lock()
_sessions: dict[str, dict] = {}


def register(serial: str) -> None:
    """Crée/réinitialise une session — appelé immédiatement au branchement USB."""
    with _lock:
        _sessions[serial] = {
            "serial":      serial,
            "status":      "CONNECTING",
            "make":        None,
            "model":       None,
            "owner_name":  None,
            "video_index": 0,
            "video_total": 0,
            "bytes_done":  0,
            "bytes_total": 0,
            "speed_bps":   0,
            "rot_labels":  [],
            "started_at":  time.time(),
            "finished_at": None,
            "error_msg":   None,
            "_samples":    [],   # [(ts, bytes_done)] pour vitesse glissante
        }


def update(serial: str, **kwargs) -> None:
    """Met à jour des champs d'une session existante."""
    with _lock:
        if serial not in _sessions:
            return
        sess = _sessions[serial]
        for k, v in kwargs.items():
            if k in sess:
                sess[k] = v


def add_bytes(serial: str, n: int) -> None:
    """Comptabilise n octets transférés et recalcule la vitesse glissante."""
    with _lock:
        if serial not in _sessions:
            return
        sess = _sessions[serial]
        sess["bytes_done"] += n
        now = time.time()
        sess["_samples"].append((now, sess["bytes_done"]))
        cutoff = now - _SPEED_WINDOW
        sess["_samples"] = [(t, b) for t, b in sess["_samples"] if t >= cutoff]
        if len(sess["_samples"]) >= 2:
            t0, b0 = sess["_samples"][0]
            t1, b1 = sess["_samples"][-1]
            dt = t1 - t0
            if dt > 0:
                sess["speed_bps"] = int((b1 - b0) / dt)


def get_all() -> list[dict]:
    """Retourne toutes les sessions actives en nettoyant celles qui ont expiré."""
    now = time.time()
    cutoff = now - _CLEANUP_AFTER
    with _lock:
        expired = [
            s for s, sess in _sessions.items()
            if sess["status"] in ("DONE", "ERROR", "UNKNOWN")
            and sess["finished_at"] is not None
            and sess["finished_at"] < cutoff
        ]
        for s in expired:
            del _sessions[s]
        return [
            {k: v for k, v in sess.items() if not k.startswith("_")}
            for sess in _sessions.values()
        ]
