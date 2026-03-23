from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin, SECRET_KEY, ALGORITHM
from app.database import get_db
from app.models.user import User
from app.models.video import Video
from app.schemas.video import VideoResponse, VideoUpdate
from jose import JWTError, jwt

router = APIRouter(prefix="/videos", tags=["Vidéos"])


@router.get("", response_model=list[VideoResponse])
def list_videos(
    user_id: Optional[int] = Query(None),
    rot_id:  Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Retourne toutes les vidéos ingérées. Filtres optionnels : user_id, rot_id."""
    q = db.query(Video)
    if user_id is not None:
        q = q.filter(Video.owner_id == user_id)
    if rot_id is not None:
        q = q.filter(Video.rot_id == rot_id)
    return q.order_by(Video.ingested_at.desc()).all()


@router.get("/rot/{rot_id}", response_model=list[VideoResponse])
def list_videos_by_rot(rot_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Retourne toutes les vidéos d'un rot (tous propriétaires confondus)."""
    return (
        db.query(Video)
        .filter(Video.rot_id == rot_id)
        .order_by(Video.owner_id, Video.camera_timestamp)
        .all()
    )


@router.get("/user/{user_id}", response_model=list[VideoResponse])
def list_videos_by_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Retourne toutes les vidéos d'un sautant donné."""
    return (
        db.query(Video)
        .filter(Video.owner_id == user_id)
        .order_by(Video.camera_timestamp.desc())
        .all()
    )


@router.get("/my-rots")
def list_videos_my_rots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retourne toutes les vidéos des rots auxquels participe l'utilisateur connecté,
    groupées par rot_id. Remplace les N+1 appels GET /videos/rot/{id} côté frontend.
    Format : { rot_id: [VideoResponse, ...] }
    """
    from app.models.rot_participant import RotParticipant

    rot_ids = [
        row[0]
        for row in db.query(RotParticipant.rot_id)
        .filter(RotParticipant.user_id == current_user.id)
        .distinct()
        .all()
    ]
    if not rot_ids:
        return {}

    videos = (
        db.query(Video)
        .filter(Video.rot_id.in_(rot_ids))
        .order_by(Video.owner_id, Video.camera_timestamp)
        .all()
    )

    result: dict[int, list] = {}
    for v in videos:
        result.setdefault(v.rot_id, []).append(v)

    # Sérialisation manuelle pour compatibilité Pydantic v2 + clés int
    from app.schemas.video import VideoResponse as VR
    return {
        rot_id: [VR.model_validate(v).model_dump(mode="json") for v in vids]
        for rot_id, vids in result.items()
    }


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Retourne le détail d'une vidéo."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    return video


@router.get("/{video_id}/download")
def download_video(
    video_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Télécharge une vidéo via X-Accel-Redirect (nginx streame directement).
    Accepte le token JWT en query param (?token=...) pour permettre
    une navigation directe sans fetch côté client.
    """
    import os

    # Authentification : Bearer header OU query param ?token=
    auth_header = request.headers.get("Authorization", "")
    raw_token = token or (auth_header.removeprefix("Bearer ").strip() or None)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token manquant.")
    try:
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré.")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable.")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    if not video.file_path or not os.path.exists(video.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier vidéo introuvable sur le disque.")

    internal_path = video.file_path.replace("/mnt/videos", "/protected-videos", 1)
    filename = os.path.basename(video.file_path)
    return Response(
        headers={
            "X-Accel-Redirect": internal_path,
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )


@router.get("/{video_id}/stream")
def stream_video(
    video_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Streaming vidéo inline via X-Accel-Redirect (pour le lecteur in-page)."""
    import os

    auth_header = request.headers.get("Authorization", "")
    raw_token = token or (auth_header.removeprefix("Bearer ").strip() or None)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token manquant.")
    try:
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide.")
    if not db.query(User).filter(User.id == user_id, User.is_active == True).first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable.")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    if not video.file_path or not os.path.exists(video.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable.")

    internal_path = video.file_path.replace("/mnt/videos", "/protected-videos", 1)
    ext = os.path.splitext(video.file_path)[1].lower()
    content_type = {"mp4": "video/mp4", "mov": "video/quicktime", "insv": "video/mp4",
                    "avi": "video/x-msvideo", "mts": "video/mp2t"}.get(ext.lstrip("."), "video/mp4")
    return Response(headers={
        "X-Accel-Redirect": internal_path,
        "Content-Type": content_type,
        "Content-Disposition": "inline",
    })


@router.get("/{video_id}/thumbnail")
def get_thumbnail(
    video_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Retourne la vignette JPEG d'une vidéo via X-Accel-Redirect."""
    import os

    auth_header = request.headers.get("Authorization", "")
    raw_token = token or (auth_header.removeprefix("Bearer ").strip() or None)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token manquant.")
    try:
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide.")
    if not db.query(User).filter(User.id == user_id, User.is_active == True).first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable.")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or not video.thumbnail_path or not os.path.exists(video.thumbnail_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vignette introuvable.")

    internal_path = video.thumbnail_path.replace("/mnt/videos", "/protected-videos", 1)
    return Response(headers={
        "X-Accel-Redirect": internal_path,
        "Content-Type": "image/jpeg",
        "Cache-Control": "max-age=86400",
    })


@router.patch("/{video_id}", response_model=VideoResponse)
def update_video(video_id: int, payload: VideoUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Réattribue une vidéo à un autre propriétaire et/ou rot."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    if payload.owner_id is not None:
        video.owner_id = payload.owner_id or None
    if payload.rot_id is not None:
        video.rot_id = payload.rot_id or None
    db.commit()
    db.refresh(video)
    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Supprime une vidéo (fichier + enregistrement DB)."""
    import os
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    if os.path.exists(video.file_path):
        os.unlink(video.file_path)
    db.delete(video)
    db.commit()
