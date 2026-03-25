import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models.settings import Settings
from app.models.user import User

LOGO_PATH = "/mnt/videos/logo.png"
LOGO_ALLOWED = {"image/png", "image/jpeg", "image/webp"}

router = APIRouter(prefix="/settings", tags=["Configuration"])


class SettingsResponse(BaseModel):
    retention_days:          int
    matching_window_minutes: int
    jump_target_delta_min:   int
    jump_window_hours:       int
    video_storage_path:      str
    notifications_enabled:   bool
    app_url:                 str | None
    smtp_host:               str | None
    smtp_port:               int
    smtp_user:               str | None
    smtp_from:               str | None

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    retention_days:          int | None = None
    matching_window_minutes: int | None = None
    jump_target_delta_min:   int | None = None
    jump_window_hours:       int | None = None
    video_storage_path:      str | None = None
    notifications_enabled:   bool | None = None
    app_url:                 str | None = None
    smtp_host:               str | None = None
    smtp_port:               int | None = None
    smtp_user:               str | None = None
    smtp_password:           str | None = None
    smtp_from:               str | None = None


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


# ── Logo du centre ────────────────────────────────────────────────────────────

@router.get("/logo")
def get_logo():
    """Sert le logo du centre (sans authentification)."""
    if not os.path.exists(LOGO_PATH):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun logo configuré.")
    return FileResponse(LOGO_PATH, media_type="image/png")


@router.post("/logo", status_code=status.HTTP_204_NO_CONTENT)
async def upload_logo(file: UploadFile = File(...), _: User = Depends(require_admin)):
    """Upload ou remplace le logo du centre (PNG/JPEG/WebP, admin uniquement)."""
    if file.content_type not in LOGO_ALLOWED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Format non supporté. PNG, JPEG ou WebP uniquement.")
    os.makedirs(os.path.dirname(LOGO_PATH), exist_ok=True)
    with open(LOGO_PATH, "wb") as f:
        shutil.copyfileobj(file.file, f)


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_logo(_: User = Depends(require_admin)):
    """Supprime le logo du centre (admin uniquement)."""
    if os.path.exists(LOGO_PATH):
        os.remove(LOGO_PATH)
