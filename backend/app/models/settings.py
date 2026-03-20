from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from app.database import Base


class Settings(Base):
    __tablename__ = "settings"

    id                      = Column(Integer, primary_key=True)
    retention_days          = Column(Integer, default=90)           # durée de rétention des vidéos
    matching_window_minutes = Column(Integer, default=45)           # fenêtre de tolérance matching (à calibrer)
    jump_target_delta_min   = Column(Integer, default=30)           # délai attendu rot_time → vidéo (minutes)
    jump_window_hours       = Column(Integer, default=2)            # fenêtre max rot_time → vidéo (heures)
    video_storage_path      = Column(String, default="/mnt/videos") # chemin de stockage des vidéos
    gmail_address           = Column(String, default="")            # compte Gmail à surveiller
    gmail_sender_filter     = Column(String, default="")            # expéditeur autorisé (ex: afifly)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
