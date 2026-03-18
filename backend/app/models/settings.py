from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from app.database import Base


class Settings(Base):
    __tablename__ = "settings"

    id                      = Column(Integer, primary_key=True)
    retention_days          = Column(Integer, default=90)           # durée de rétention des vidéos
    matching_window_minutes = Column(Integer, default=45)           # fenêtre de tolérance matching (à calibrer)
    video_storage_path      = Column(String, default="/mnt/videos") # chemin de stockage des vidéos
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
