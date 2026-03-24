from datetime import datetime
from pydantic import BaseModel


class UserCreate(BaseModel):
    """Création d'un compte par l'admin."""
    first_name:  str
    last_name:   str
    email:       str
    password:    str
    afifly_name: str | None = None
    is_admin:    bool = False


class OnboardingRequest(BaseModel):
    """Création de compte en self-service depuis le kiosque."""
    first_name:      str
    last_name:       str
    email:           str
    password:        str
    afifly_name:     str | None = None
    camera_serials:  list[str] = []


class UserSelfUpdate(BaseModel):
    """Mise à jour du profil par l'utilisateur lui-même."""
    first_name:             str | None = None
    last_name:              str | None = None
    email:                  str | None = None
    afifly_name:            str | None = None
    password:               str | None = None   # nouveau mot de passe (optionnel)
    notifications_enabled:  bool | None = None


class UserUpdate(BaseModel):
    """Mise à jour partielle d'un utilisateur (admin uniquement)."""
    first_name:            str | None = None
    last_name:             str | None = None
    email:                 str | None = None
    afifly_name:           str | None = None
    password:              str | None = None
    camera_serials:        list[str] | None = None
    is_admin:              bool | None = None
    is_active:             bool | None = None
    notifications_enabled: bool | None = None


class UserUpdateCameras(BaseModel):
    """Mise à jour des caméras associées à un sautant."""
    camera_serials: list[str]


class UserResponse(BaseModel):
    """Données retournées par l'API (le mot de passe n'est jamais exposé)."""
    id:                    int
    first_name:            str
    last_name:             str
    email:                 str | None
    camera_serials:        list[str]
    afifly_name:           str | None
    is_admin:              bool
    is_active:             bool
    notifications_enabled: bool
    created_at:            datetime

    class Config:
        from_attributes = True
