from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    first_name       = Column(String, nullable=False)
    last_name        = Column(String, nullable=False)
    email            = Column(String, unique=True, nullable=True, index=True)
    password_hash    = Column(String, nullable=True)     # conservé pour compatibilité migration
    pin_lookup_hash  = Column(String, unique=True, nullable=True, index=True)  # HMAC-SHA256 du PIN
    camera_serials   = Column(ARRAY(String), default=[])
    afifly_name      = Column(String)                    # nom tel qu'il apparaît dans les PDFs Afifly
    is_admin         = Column(Boolean, default=False)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
