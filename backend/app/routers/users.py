import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, pin_to_lookup_hash, require_admin
from app.database import get_db
from app.models.rot_participant import RotParticipant
from app.models.user import User
from app.models.video import Video
from app.auth import get_current_user
from app.schemas.user import OnboardingRequest, UserCreate, UserResponse, UserSelfUpdate, UserUpdate, UserUpdateCameras

router = APIRouter(prefix="/users", tags=["Utilisateurs"])
logger = logging.getLogger(__name__)


def _validate_pin(pin: str, is_admin: bool) -> None:
    """Valide le format du PIN : 4 chiffres pour sautant, 6 pour admin."""
    expected = 6 if is_admin else 4
    if not pin.isdigit() or len(pin) != expected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Le PIN doit contenir exactement {expected} chiffres.",
        )


def _pin_unique(pin_hash: str, db: Session, exclude_id: int | None = None) -> None:
    """Vérifie que le PIN n'est pas déjà utilisé."""
    q = db.query(User).filter(User.pin_lookup_hash == pin_hash)
    if exclude_id:
        q = q.filter(User.id != exclude_id)
    if q.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce PIN est déjà utilisé par un autre compte.",
        )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Crée un compte sautant (réservé à l'admin)."""
    _validate_pin(payload.pin, payload.is_admin)
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé.")
    lookup = pin_to_lookup_hash(payload.pin)
    _pin_unique(lookup, db)
    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email or None,
        pin_lookup_hash=lookup,
        afifly_name=payload.afifly_name or None,
        camera_serials=[],
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"[USERS] Compte créé par admin : {user.first_name} {user.last_name} (id={user.id})")
    return user


@router.post("/onboard", response_model=dict, status_code=status.HTTP_201_CREATED)
def onboard(payload: OnboardingRequest, db: Session = Depends(get_db)):
    """
    Crée un compte depuis le kiosque (self-service, sans authentification).
    PIN : exactement 4 chiffres.
    Les serials sélectionnés par l'utilisateur sont associés et l'ingestion démarre.
    """
    import threading
    from app.routers.internal import get_pending_cameras, remove_pending_camera
    from app.services.video_ingestor import ingest_device, ingest_gopro_http, ingest_mtp_device

    _validate_pin(payload.pin, is_admin=False)
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé.")
    lookup = pin_to_lookup_hash(payload.pin)
    _pin_unique(lookup, db)

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email or None,
        pin_lookup_hash=lookup,
        afifly_name=payload.afifly_name or None,
        camera_serials=list(payload.camera_serials),
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(
        f"[ONBOARDING] Compte créé : {user.first_name} {user.last_name} "
        f"(id={user.id}, serials={payload.camera_serials})"
    )

    # Pour chaque serial sélectionné, démarrer l'ingestion si la caméra est en attente
    pending_map = {c["serial"]: c for c in get_pending_cameras()}
    for serial in payload.camera_serials:
        cam = pending_map.get(serial)
        if not cam:
            continue
        mtp         = cam.get("mtp", False)
        vendor_id   = cam.get("vendor_id")
        device_node = cam.get("device_node")

        def _run(s=serial, m=mtp, v=vendor_id, d=device_node):
            from app.database import SessionLocal
            idb = SessionLocal()
            try:
                if m and v == "2672":
                    ingest_gopro_http(serial=s, db=idb)
                elif m:
                    ingest_mtp_device(serial=s, db=idb)
                elif d:
                    ingest_device(device_node=d, serial=s, db=idb)
            finally:
                idb.close()

        threading.Thread(target=_run, daemon=True).start()
        remove_pending_camera(serial)

    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_admin": user.is_admin,
            "camera_serials": user.camera_serials,
            "afifly_name": user.afifly_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retourne le profil de l'utilisateur connecté."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(payload: UserSelfUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Met à jour le profil de l'utilisateur connecté (nom, email, afifly, PIN)."""
    if payload.first_name is not None:
        current_user.first_name = payload.first_name
    if payload.last_name is not None:
        current_user.last_name = payload.last_name
    if payload.email is not None:
        if payload.email and db.query(User).filter(User.email == payload.email, User.id != current_user.id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé.")
        current_user.email = payload.email or None
    if payload.afifly_name is not None:
        current_user.afifly_name = payload.afifly_name or None
    if payload.pin is not None:
        _validate_pin(payload.pin, current_user.is_admin)
        lookup = pin_to_lookup_hash(payload.pin)
        _pin_unique(lookup, db, exclude_id=current_user.id)
        current_user.pin_lookup_hash = lookup
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me/cameras/{serial}", response_model=UserResponse)
def remove_my_camera(serial: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Supprime une caméra de la liste de l'utilisateur connecté."""
    current_user.camera_serials = [s for s in current_user.camera_serials if s != serial]
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/cameras/claim", response_model=UserResponse)
def claim_camera(body: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Associe une caméra au compte de l'utilisateur connecté.
    Si la caméra est dans la liste pending, démarre l'ingestion et la retire du pending.
    Accepte {serial} ou {serial, manual: true} pour une saisie manuelle.
    """
    import threading
    from app.routers.internal import get_pending_cameras, remove_pending_camera
    from app.services.video_ingestor import ingest_device, ingest_gopro_http, ingest_mtp_device

    serial = body.get("serial", "").strip()
    if not serial:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Serial requis.")
    if serial in current_user.camera_serials:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette caméra est déjà associée à votre compte.")
    if db.query(User).filter(User.camera_serials.contains([serial]), User.is_active == True).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette caméra est déjà associée à un autre compte.")

    current_user.camera_serials = current_user.camera_serials + [serial]
    db.commit()
    db.refresh(current_user)

    # Démarrer l'ingestion si la caméra est dans le pending
    pending_map = {c["serial"]: c for c in get_pending_cameras()}
    cam = pending_map.get(serial)
    if cam:
        mtp, vendor_id, device_node = cam.get("mtp", False), cam.get("vendor_id"), cam.get("device_node")

        def _run():
            from app.database import SessionLocal
            idb = SessionLocal()
            try:
                if mtp and vendor_id == "2672":
                    ingest_gopro_http(serial=serial, db=idb)
                elif mtp:
                    ingest_mtp_device(serial=serial, db=idb)
                elif device_node:
                    ingest_device(device_node=device_node, serial=serial, db=idb)
            finally:
                idb.close()

        threading.Thread(target=_run, daemon=True).start()
        remove_pending_camera(serial)
        logger.info(f"[USERS/ME] Caméra associée + ingestion démarrée : {serial} → user {current_user.id}")
    else:
        logger.info(f"[USERS/ME] Caméra associée (manuelle) : {serial} → user {current_user.id}")

    return current_user


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


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Met à jour un compte sautant (réservé à l'admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sautant introuvable.")
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.email is not None:
        if payload.email and db.query(User).filter(User.email == payload.email, User.id != user_id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé.")
        user.email = payload.email or None
    if payload.afifly_name is not None:
        user.afifly_name = payload.afifly_name or None
    if payload.camera_serials is not None:
        user.camera_serials = payload.camera_serials
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.pin is not None:
        effective_admin = payload.is_admin if payload.is_admin is not None else user.is_admin
        _validate_pin(payload.pin, effective_admin)
        lookup = pin_to_lookup_hash(payload.pin)
        _pin_unique(lookup, db, exclude_id=user_id)
        user.pin_lookup_hash = lookup
    db.commit()
    db.refresh(user)
    logger.info(f"[USERS] Compte mis à jour par admin : id={user_id}")
    return user


@router.patch("/{user_id}/cameras", response_model=UserResponse)
def update_cameras(user_id: int, payload: UserUpdateCameras, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Met à jour les numéros de série des caméras associées à un sautant."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sautant introuvable.")
    user.camera_serials = payload.camera_serials
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Désactive un compte sautant (soft delete)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sautant introuvable.")
    user.is_active = False
    db.commit()


@router.delete("/{user_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """
    Supprime définitivement un compte sautant ainsi que toutes ses vidéos (fichiers + DB)
    et ses participations aux rotations.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sautant introuvable.")

    # Supprimer les fichiers vidéo sur disque
    videos = db.query(Video).filter(Video.owner_id == user_id).all()
    for v in videos:
        if v.file_path and os.path.exists(v.file_path):
            try:
                os.unlink(v.file_path)
            except OSError:
                pass

    # Supprimer les enregistrements DB liés
    db.query(Video).filter(Video.owner_id == user_id).delete()
    db.query(RotParticipant).filter(RotParticipant.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    logger.info(f"[USERS] Compte supprimé définitivement : id={user_id}")
