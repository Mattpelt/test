from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.video import Video
from app.schemas.video import VideoResponse

router = APIRouter(prefix="/videos", tags=["Vidéos"])


@router.get("", response_model=list[VideoResponse])
def list_videos(db: Session = Depends(get_db)):
    """Retourne toutes les vidéos ingérées, de la plus récente à la plus ancienne."""
    return db.query(Video).order_by(Video.ingested_at.desc()).all()


@router.get("/user/{user_id}", response_model=list[VideoResponse])
def list_videos_by_user(user_id: int, db: Session = Depends(get_db)):
    """Retourne toutes les vidéos d'un sautant donné."""
    return (
        db.query(Video)
        .filter(Video.owner_id == user_id)
        .order_by(Video.camera_timestamp.desc())
        .all()
    )


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    """Retourne le détail d'une vidéo."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, db: Session = Depends(get_db)):
    """Supprime une vidéo (fichier + enregistrement DB)."""
    import os
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vidéo introuvable.")
    if os.path.exists(video.file_path):
        os.unlink(video.file_path)
    db.delete(video)
    db.commit()
