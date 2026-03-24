"""
Dashboard de monitoring admin — métriques système, BDD et vidéos.
GET /admin/stats   (admin only)
"""
import shutil
from datetime import datetime, date

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin
from app.models.user import User
from app.models.video import Video
from app.models.rot import Rot
from app.models.settings import Settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    # ── Utilisateurs ──────────────────────────────────────────────
    total_users  = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users  = db.query(User).filter(User.is_admin == True, User.is_active == True).count()

    # ── Vidéos ────────────────────────────────────────────────────
    videos = db.query(Video).all()
    total_videos = len(videos)
    total_size   = sum(v.file_size_bytes or 0 for v in videos)
    matched      = sum(1 for v in videos if v.matching_status == "MATCHED")
    unmatched    = sum(1 for v in videos if v.matching_status == "UNMATCHED")
    ambiguous    = sum(1 for v in videos if v.matching_status == "AMBIGUOUS")
    manual       = sum(1 for v in videos if v.matching_status == "MANUAL")

    # ── Rotations ─────────────────────────────────────────────────
    total_rots = db.query(Rot).count()
    today_rots = db.query(Rot).filter(Rot.rot_date == date.today()).count()

    # ── Disque ────────────────────────────────────────────────────
    settings   = db.query(Settings).first()
    video_path = (settings.video_storage_path if settings else None) or "/mnt/videos"
    disk_total = disk_used = disk_free = None
    try:
        disk       = shutil.disk_usage(video_path)
        disk_total = disk.total
        disk_used  = disk.used
        disk_free  = disk.free
    except Exception:
        pass

    # ── Système (psutil) ──────────────────────────────────────────
    cpu_percent = ram_total = ram_used = ram_percent = uptime_seconds = None
    try:
        cpu_percent    = psutil.cpu_percent(interval=0.3)
        ram            = psutil.virtual_memory()
        ram_total      = ram.total
        ram_used       = ram.used
        ram_percent    = ram.percent
        uptime_seconds = int(datetime.now().timestamp() - psutil.boot_time())
    except Exception:
        pass

    # ── Vidéos récentes (10 dernières) ────────────────────────────
    recent_rows = (
        db.query(Video, User)
        .outerjoin(User, Video.owner_id == User.id)
        .order_by(Video.ingested_at.desc())
        .limit(10)
        .all()
    )
    recent_videos = [
        {
            "id":               v.id,
            "file_name":        v.file_name,
            "file_size_bytes":  v.file_size_bytes,
            "camera_timestamp": v.camera_timestamp.isoformat() if v.camera_timestamp else None,
            "ingested_at":      v.ingested_at.isoformat()      if v.ingested_at      else None,
            "matching_status":  v.matching_status,
            "owner":            f"{u.first_name} {u.last_name}" if u else None,
        }
        for v, u in recent_rows
    ]

    return {
        "users": {
            "total":  total_users,
            "active": active_users,
            "admins": admin_users,
        },
        "videos": {
            "total":            total_videos,
            "total_size_bytes": total_size,
            "matched":          matched,
            "unmatched":        unmatched,
            "ambiguous":        ambiguous,
            "manual":           manual,
        },
        "rots": {
            "total": total_rots,
            "today": today_rots,
        },
        "disk": {
            "path":  video_path,
            "total": disk_total,
            "used":  disk_used,
            "free":  disk_free,
        },
        "system": {
            "cpu_percent":    cpu_percent,
            "ram_total":      ram_total,
            "ram_used":       ram_used,
            "ram_percent":    ram_percent,
            "uptime_seconds": uptime_seconds,
        },
        "recent_videos": recent_videos,
    }
