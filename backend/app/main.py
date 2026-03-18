from fastapi import FastAPI
from app.database import Base, engine
from app import models  # noqa: F401 — importer les modèles pour que SQLAlchemy les enregistre

app = FastAPI(title="SkyDive Media Hub", version="0.1.0")


@app.on_event("startup")
def create_tables():
    """Crée toutes les tables en base de données au démarrage si elles n'existent pas."""
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    """Endpoint de vérification : le backend est-il en vie ?"""
    return {"status": "ok"}
