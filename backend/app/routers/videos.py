from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models.user import User
from app.models.video import Video
from app.schemas.video import VideoResponse

router = APIRouter(prefix="/videos", tags=["Vidéos"])


@router.get("", response_model=list[VideoResponse])
def list_videos(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Retourne toutes les vidéos ingérées, de la plus récente à la plus ancienne."""
    return db.query(Video).order_by(Video.ingested_at.desc()).all()


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


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Retourne le détail d'une vidéo."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    return video


@router.get("/{video_id}/download")
def download_video(video_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """
    Télécharge une vidéo.
    Utilise X-Accel-Redirect quand nginx est présent (production),
    sinon FileResponse direct (développement).
    """
    import os
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    if not video.file_path or not os.path.exists(video.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier vidéo introuvable sur le disque.")

    # X-Accel-Redirect : nginx sert le fichier directement (performances optimales)
    # Le chemin interne nginx /protected-videos/ est mappé vers VIDEO_STORAGE_PATH
    internal_path = video.file_path.replace("/mnt/videos", "/protected-videos", 1)
    filename = os.path.basename(video.file_path)
    return Response(
        headers={
            "X-Accel-Redirect": internal_path,
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )


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
