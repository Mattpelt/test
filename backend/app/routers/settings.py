from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models.settings import Settings
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["Configuration"])


class SettingsResponse(BaseModel):
    retention_days:          int
    matching_window_minutes: int
    jump_target_delta_min:   int
    jump_window_hours:       int
    video_storage_path:      str

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    retention_days:          int | None = None
    matching_window_minutes: int | None = None
    jump_target_delta_min:   int | None = None
    jump_window_hours:       int | None = None
    video_storage_path:      str | None = None


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Retourne la configuration actuelle."""
    s = db.query(Settings).first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings introuvables.")
    return s


@router.patch("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Met à jour un ou plusieurs paramètres de configuration."""
    s = db.query(Settings).first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings introuvables.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(s, field, value)

    db.commit()
    db.refresh(s)
    return s
