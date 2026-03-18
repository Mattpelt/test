from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from app.database import Base


class Video(Base):
    __tablename__ = "videos"

    id               = Column(Integer, primary_key=True, index=True)
    file_name        = Column(String, nullable=False)
    file_path        = Column(String, nullable=False)
    file_format      = Column(String)                              # MP4, MOV, INSV...
    file_size_bytes  = Column(BigInteger)
    camera_timestamp = Column(DateTime, nullable=False)            # horodatage lu sur le fichier vidéo
    owner_id         = Column(Integer, ForeignKey("users.id"))
    rot_id           = Column(Integer, ForeignKey("rots.id"), nullable=True)   # NULL si non matché
    group_id         = Column(Integer, nullable=True)              # groupe dans le rot
    matching_status  = Column(String, default="UNMATCHED")         # MATCHED / AMBIGUOUS / UNMATCHED
    ingested_at      = Column(DateTime, default=datetime.utcnow)
    expires_at       = Column(DateTime)                            # calculé à l'ingestion selon rétention
