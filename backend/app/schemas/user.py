from datetime import datetime
from pydantic import BaseModel


class UserCreate(BaseModel):
    """Création d'un compte par l'admin. PIN : 4 chiffres (sautant) ou 6 chiffres (admin)."""
    first_name:  str
    last_name:   str
    email:       str | None = None
    pin:         str
    afifly_name: str | None = None
    is_admin:    bool = False


class OnboardingRequest(BaseModel):
    """Création de compte en self-service depuis le kiosque."""
    first_name:      str
    last_name:       str
    email:           str | None = None
    afifly_name:     str | None = None
    pin:             str           # exactement 4 chiffres
    camera_serial:   str | None = None  # serial détecté automatiquement


class UserUpdate(BaseModel):
    """Mise à jour partielle d'un utilisateur (admin uniquement)."""
    first_name:     str | None = None
    last_name:      str | None = None
    email:          str | None = None
    afifly_name:    str | None = None
    pin:            str | None = None
    camera_serials: list[str] | None = None
    is_admin:       bool | None = None
    is_active:      bool | None = None


class UserUpdateCameras(BaseModel):
    """Mise à jour des caméras associées à un sautant."""
    camera_serials: list[str]


class UserResponse(BaseModel):
    """Données retournées par l'API (le PIN n'est jamais exposé)."""
    id:             int
    first_name:     str
    last_name:      str
    email:          str | None
    camera_serials: list[str]
    afifly_name:    str | None
    is_admin:       bool
    is_active:      bool
    created_at:     datetime

    class Config:
        from_attributes = True
