import logging
from fastapi import FastAPI
from sqlalchemy import text
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
    """Au démarrage : création des tables, migrations, settings par défaut, surveillant USB."""
    Base.metadata.create_all(bind=engine)
    _migrate()
    _init_settings()
    start_usb_watcher()


def _migrate():
    """Migrations manuelles — ADD COLUMN IF NOT EXISTS pour les nouvelles colonnes."""
    migrations = [
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS jump_target_delta_min INTEGER DEFAULT 30",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS jump_window_hours INTEGER DEFAULT 2",
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS rot_id INTEGER REFERENCES rots(id)",
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS group_id INTEGER",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.warning(f"Migration ignorée ({e}): {sql[:60]}")
        conn.commit()


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
