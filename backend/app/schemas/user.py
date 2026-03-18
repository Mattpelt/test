from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Données requises pour créer un compte sautant."""
    first_name:   str
    last_name:    str
    email:        EmailStr
    password:     str
    afifly_name:  str | None = None   # nom tel qu'il apparaît dans les PDFs Afifly
    is_admin:     bool = False


class UserUpdateCameras(BaseModel):
    """Mise à jour des caméras associées à un sautant."""
    camera_serials: list[str]


class UserResponse(BaseModel):
    """Données retournées par l'API (le mot de passe n'est jamais exposé)."""
    id:             int
    first_name:     str
    last_name:      str
    email:          str
    camera_serials: list[str]
    afifly_name:    str | None
    is_admin:       bool
    is_active:      bool
    created_at:     datetime

    class Config:
        from_attributes = True   # permet de convertir un objet SQLAlchemy en schéma
