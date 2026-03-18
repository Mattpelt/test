from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    first_name     = Column(String, nullable=False)
    last_name      = Column(String, nullable=False)
    email          = Column(String, unique=True, nullable=False, index=True)
    password_hash  = Column(String, nullable=False)
    camera_serials = Column(ARRAY(String), default=[])   # ex: ["SN-GOPRO-12345", "SN-INSTA-67890"]
    afifly_name    = Column(String)                      # nom tel qu'il apparaît dans les PDFs Afifly
    is_admin       = Column(Boolean, default=False)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
