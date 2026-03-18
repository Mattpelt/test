from sqlalchemy import Column, ForeignKey, Integer, String
from app.database import Base


class RotParticipant(Base):
    __tablename__ = "rot_participants"

    id          = Column(Integer, primary_key=True, index=True)
    rot_id      = Column(Integer, ForeignKey("rots.id"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL si pas encore matché
    afifly_name = Column(String, nullable=False)  # nom tel qu'il apparaît dans le PDF
    level       = Column(String)                  # A / B / BPA / C / D
    weight      = Column(Integer)                 # poids en kg
    jump_type   = Column(String)                  # ex : FS4, VRW, AFF...
    group_id    = Column(Integer)                 # numéro du groupe dans ce rot (1, 2, 3...)
