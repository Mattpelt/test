from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Integer, String, Time
from sqlalchemy.orm import relationship
from app.database import Base


class Rot(Base):
    __tablename__ = "rots"

    id                 = Column(Integer, primary_key=True, index=True)
    rot_number         = Column(Integer, nullable=False)       # numéro global (ex : 1631)
    day_number         = Column(Integer)                       # numéro dans la journée (ex : 9)
    rot_date           = Column(Date, nullable=False)
    rot_time           = Column(Time, nullable=False)          # heure officielle du rot
    plane_registration = Column(String)                        # immatriculation avion
    pilot              = Column(String)
    chef_avion         = Column(String)
    source_pdf_path    = Column(String)                        # chemin du PDF source archivé
    parse_status       = Column(String, default="OK")          # OK / ERREUR
    parsed_at          = Column(DateTime, default=datetime.utcnow)

    participants       = relationship("RotParticipant", back_populates="rot", lazy="selectin")
