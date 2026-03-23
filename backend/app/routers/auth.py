from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, pin_to_lookup_hash
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentification"])


class LoginRequest(BaseModel):
    pin: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authentifie un utilisateur par son PIN et retourne un JWT valable 7 jours."""
    lookup = pin_to_lookup_hash(payload.pin)
    user = db.query(User).filter(User.pin_lookup_hash == lookup, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorrect.",
        )
    return {"access_token": create_access_token(user.id)}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Retourne le profil de l'utilisateur connecté."""
    return current_user
