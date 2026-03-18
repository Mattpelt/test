import logging
from fastapi import FastAPI
from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401 — enregistre les modèles auprès de SQLAlchemy
from app.models.settings import Settings
from app.services.usb_watcher import start_usb_watcher
from app.routers import users, rots, videos, internal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="SkyDive Media Hub", version="0.1.0")

app.include_router(users.router)
app.include_router(rots.router)
app.include_router(videos.router)
app.include_router(internal.router)


@app.on_event("startup")
def on_startup():
    """Au démarrage : création des tables, settings par défaut, surveillant USB."""
    Base.metadata.create_all(bind=engine)
    _init_settings()
    start_usb_watcher()


def _init_settings():
    """Crée la ligne de configuration par défaut si elle n'existe pas encore."""
    db = SessionLocal()
    try:
        if not db.query(Settings).first():
            db.add(Settings())
            db.commit()
            logger.info("Settings initialisés avec les valeurs par défaut.")
    finally:
        db.close()


@app.get("/health")
def health():
    """Vérifie que le backend est en vie."""
    return {"status": "ok"}
