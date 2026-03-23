from datetime import datetime
from sqlalchemy import Column, DateTime, String
from app.database import Base


class Camera(Base):
    """
    Registre des caméras connues du système.
    Peuplé automatiquement à chaque ingestion vidéo.
    - serial     : identifiant canonique (= vrai serial depuis les métadonnées vidéo)
    - usb_serial : serial USB brut (peut être "0001" pour Insta360 en mode Mass Storage)
    - make       : marque  ("GoPro", "Insta360", "Sony"…)
    - model      : modèle  ("HERO12 Black", "X5", "ZV-1"…)
    - vendor_id  : identifiant USB (ex: "2672" pour GoPro)
    """
    __tablename__ = "cameras"

    serial     = Column(String, primary_key=True)
    usb_serial = Column(String, nullable=True, index=True)
    make       = Column(String, nullable=True)
    model      = Column(String, nullable=True)
    vendor_id  = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
