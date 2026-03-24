"""
Endpoint public — état temps réel des caméras connectées.
Aucune authentification requise (pas de données sensibles).
"""
from fastapi import APIRouter
from app import camera_state

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("/live")
def get_cameras_live():
    return camera_state.get_all()
