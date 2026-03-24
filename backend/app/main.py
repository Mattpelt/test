import logging
from fastapi import FastAPI


class _SuppressPolling(logging.Filter):
    """Filtre les requêtes de polling répétitives des logs d'accès uvicorn."""
    _SUPPRESSED = {"/internal/onboarding/pending", "/health"}

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(path in msg for path in self._SUPPRESSED)

from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401 — enregistre les modèles auprès de SQLAlchemy
from app.models.settings import Settings
from app.services.usb_watcher import start_usb_watcher
from app.services.retention import cleanup_expired_videos
from app.routers import auth, users, rots, videos, internal, settings, admin_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="SkyDive Media Hub", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(rots.router)
app.include_router(videos.router)
app.include_router(internal.router)
app.include_router(settings.router)
app.include_router(admin_stats.router)


@app.on_event("startup")
def on_startup():
    # Filtrer le polling sur tous les loggers/handlers uvicorn + root
    _f = _SuppressPolling()
    for name in ("uvicorn.access", "uvicorn", ""):
        lgr = logging.getLogger(name)
        lgr.addFilter(_f)
        for hdlr in lgr.handlers:
            hdlr.addFilter(_f)
    """Au démarrage : création des tables, migrations, settings par défaut, surveillant USB."""
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  SkyDive Media Hub — Démarrage")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    Base.metadata.create_all(bind=engine)
    logger.info("Base de données : tables vérifiées / créées.")
    _migrate()
    _init_settings()
    start_usb_watcher()
    _start_scheduler()
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  Démarrage terminé — prêt à recevoir des requêtes.")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def _migrate():
    """Migrations manuelles — ADD COLUMN IF NOT EXISTS pour les nouvelles colonnes."""
    migrations = [
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS jump_target_delta_min INTEGER DEFAULT 30",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS jump_window_hours INTEGER DEFAULT 2",
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS rot_id INTEGER REFERENCES rots(id)",
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS group_id INTEGER",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS app_url VARCHAR DEFAULT 'http://192.168.1.39'",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS smtp_host VARCHAR",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS smtp_port INTEGER DEFAULT 587",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS smtp_user VARCHAR",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS smtp_password VARCHAR",
        "ALTER TABLE settings ADD COLUMN IF NOT EXISTS smtp_from VARCHAR",
        # Vignettes vidéo
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_path VARCHAR",
        # Notifications par utilisateur
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN DEFAULT TRUE",
        # Authentification par PIN
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS pin_lookup_hash VARCHAR",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_pin_lookup_hash ON users (pin_lookup_hash) WHERE pin_lookup_hash IS NOT NULL",
        "ALTER TABLE users ALTER COLUMN email DROP NOT NULL",
        "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL",
    ]
    with engine.connect() as conn:
        applied = 0
        for sql in migrations:
            try:
                conn.execute(text(sql))
                applied += 1
            except Exception as e:
                logger.warning(f"Migration ignorée ({e}): {sql[:60]}")
        conn.commit()
    logger.info(f"Migrations : {applied}/{len(migrations)} appliquées.")


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


def _start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired_videos, "cron", hour=3, minute=0, id="retention_cleanup")
    scheduler.start()
    logger.info("Scheduler démarré — nettoyage rétention planifié à 03:00 chaque jour.")


@app.get("/health")
def health():
    """Vérifie que le backend est en vie."""
    return {"status": "ok"}
