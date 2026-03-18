import logging
from fastapi import FastAPI
from app.database import Base, engine
from app import models  # noqa: F401 — enregistre les modèles auprès de SQLAlchemy
from app.services.usb_watcher import start_usb_watcher
from app.routers import users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

app = FastAPI(title="SkyDive Media Hub", version="0.1.0")

app.include_router(users.router)


@app.on_event("startup")
def on_startup():
    """Au démarrage : création des tables + lancement du surveillant USB."""
    Base.metadata.create_all(bind=engine)
    start_usb_watcher()


@app.get("/health")
def health():
    """Vérifie que le backend est en vie."""
    return {"status": "ok"}
