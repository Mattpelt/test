from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.auth import require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdateCameras

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Crée un nouveau compte sautant."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte avec cet email existe déjà.",
        )
    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=pwd_context.hash(payload.password),
        afifly_name=payload.afifly_name,
        camera_serials=[],
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Retourne la liste de tous les sautants actifs."""
    return db.query(User).filter(User.is_active == True).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Retourne le profil d'un sautant."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sautant introuvable.")
    return user


@router.patch("/{user_id}/cameras", response_model=UserResponse)
def update_cameras(user_id: int, payload: UserUpdateCameras, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """
    Met à jour les numéros de série des caméras associées à un sautant.
    Remplace la liste complète (ajouter ou retirer une caméra).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sautant introuvable.")
    user.camera_serials = payload.camera_serials
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """
    Désactive un compte sautant (soft delete).
    Le compte reste en base pour conserver l'historique des vidéos.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sautant introuvable.")
    user.is_active = False
    db.commit()
