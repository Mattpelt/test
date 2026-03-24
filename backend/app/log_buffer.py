"""
Buffer circulaire des logs backend — expose les 500 dernières entrées
en excluant uniquement les accès HTTP (uvicorn.access).
"""
import logging
from collections import deque
from datetime import datetime, timezone

_MAX = 500

# Loggers à ignorer (requêtes HTTP routinières)
_EXCLUDED_LOGGERS = {"uvicorn.access"}


class _BufferHandler(logging.Handler):
    def __init__(self, buf: deque):
        super().__init__(level=logging.DEBUG)
        self._buf = buf

    def emit(self, record: logging.LogRecord):
        if record.name in _EXCLUDED_LOGGERS:
            return
        self._buf.append({
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        })


_buf: deque = deque(maxlen=_MAX)
_handler = _BufferHandler(_buf)


def install():
    """Branche le handler sur le root logger — à appeler une fois au démarrage."""
    logging.getLogger().addHandler(_handler)


def get_logs(limit: int = 200) -> list[dict]:
    """Retourne les N dernières entrées, les plus récentes en premier."""
    entries = list(_buf)
    entries.reverse()
    return entries[:min(limit, _MAX)]
