import os
import tempfile

import pdfplumber
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rot import Rot
from app.models.rot_participant import RotParticipant
from app.models.user import User
from app.schemas.rot import RotInput, RotResponse
from app.services.pdf_parser import parse_afifly_pdf

router = APIRouter(prefix="/rots", tags=["Rotations"])


def _persist_rot(data: dict, db: Session, source_pdf_path: str | None = None) -> Rot:
    """
    Persiste un rot et ses participants en base.
    Tente de matcher chaque participant avec un compte utilisateur existant (via afifly_name).
    """
    rot = Rot(
        rot_number         = data["rot_number"],
        day_number         = data.get("day_number"),
        rot_date           = data["rot_date"],
        rot_time           = data["rot_time"],
        plane_registration = data.get("plane_registration"),
        pilot              = data.get("pilot"),
        chef_avion         = data.get("chef_avion"),
        source_pdf_path    = source_pdf_path,
        parse_status       = "OK",
    )
    db.add(rot)
    db.flush()

    matched = 0
    for p in data.get("participants", []):
        user = (
            db.query(User)
            .filter(User.afifly_name == p["afifly_name"], User.is_active == True)
            .first()
        )
        if user:
            matched += 1
        db.add(RotParticipant(
            rot_id      = rot.id,
            user_id     = user.id if user else None,
            afifly_name = p["afifly_name"],
            level       = p.get("level"),
            weight      = p.get("weight"),
            jump_type   = p.get("jump_type"),
            group_id    = p.get("group_id", 1),
        ))

    db.commit()
    db.refresh(rot)

    total = len(data.get("participants", []))
    print(f"Rot n°{rot.rot_number} enregistré — {total} participants, {matched} matchés.")
    return rot


@router.post("/debug-pdf")
def debug_pdf(file: UploadFile = File(...)):
    """
    Retourne la structure brute pdfplumber du PDF (tables, colonnes, rects).
    Endpoint de diagnostic uniquement — à supprimer en production.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        with pdfplumber.open(tmp_path) as pdf:
            page = pdf.pages[0]

            tables_info = []
            for i, t in enumerate(page.find_tables()):
                rows = t.extract()
                tables_info.append({
                    "table_index": i,
                    "bbox": t.bbox,
                    "num_rows": len(rows),
                    "first_3_rows": rows[:3],
                })

            rects_info = [
                {"top": r["top"], "bottom": r["bottom"],
                 "width": round(r["width"], 1), "height": round(r["height"], 1)}
                for r in page.rects
            ]

            # Tous les edges horizontaux avec leurs coordonnées complètes
            all_h_edges = sorted([
                {
                    "top":       round(e.get("top", 0), 2),
                    "x0":        round(e.get("x0", 0), 2),
                    "x1":        round(e.get("x1", 0), 2),
                    "linewidth": round(e.get("linewidth", 0), 2),
                }
                for e in page.edges
                if e.get("orientation") == "h"
            ], key=lambda e: e["top"])

            # Mots de la page avec position (filtrés sur la moitié basse = participants)
            page_mid = page.height / 2
            participant_words = [
                {
                    "text": w["text"],
                    "top":  round(w["top"], 2),
                    "x0":   round(w["x0"], 2),
                }
                for w in page.extract_words()
                if w["top"] > page_mid
            ]

            return {
                "num_tables": len(tables_info),
                "tables": tables_info,
                "num_rects": len(rects_info),
                "rects": rects_info,
                "all_horizontal_edges": all_h_edges,
                "participant_area_words": participant_words,
            }
    finally:
        os.unlink(tmp_path)


@router.post("/parse-preview")
def parse_preview(file: UploadFile = File(...)):
    """
    Upload un PDF Afifly et retourne les données parsées SANS les sauvegarder.
    Utile pour valider le parser sur un nouveau PDF avant ingestion réelle.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit être un PDF.",
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        result = parse_afifly_pdf(tmp_path)
        # Convertir date/time en str pour la sérialisation JSON
        result["rot_date"] = str(result.get("rot_date", ""))
        result["rot_time"] = str(result.get("rot_time", ""))
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur de parsing : {e}",
        )
    finally:
        os.unlink(tmp_path)


@router.post("", response_model=RotResponse, status_code=status.HTTP_201_CREATED)
def create_rot_from_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload un PDF Afifly, parse et sauvegarde le rot en base de données.
    Tente également de matcher chaque participant avec un compte utilisateur existant.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit être un PDF.",
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        data = parse_afifly_pdf(tmp_path)
    except ValueError as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur de parsing : {e}",
        )

    # Vérifier si ce rot existe déjà
    existing = db.query(Rot).filter(
        Rot.rot_number == data["rot_number"],
        Rot.rot_date   == data["rot_date"],
    ).first()
    if existing:
        os.unlink(tmp_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le rot n°{data['rot_number']} du {data['rot_date']} existe déjà.",
        )

    rot = _persist_rot(data, db, source_pdf_path=tmp_path)
    return rot


@router.post("/json", response_model=RotResponse, status_code=status.HTTP_201_CREATED)
def create_rot_from_json(payload: RotInput, db: Session = Depends(get_db)):
    """
    Crée un rot directement depuis un payload JSON, sans PDF.

    Utilisations :
    - Tests et debug (simuler une rotation sans générer un PDF)
    - Intégration future avec une API Afifly ou tout autre système externe
      capable d'envoyer les données de rotation en JSON
    """
    existing = db.query(Rot).filter(
        Rot.rot_number == payload.rot_number,
        Rot.rot_date   == payload.rot_date,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le rot n°{payload.rot_number} du {payload.rot_date} existe déjà.",
        )

    data = {
        "rot_number":         payload.rot_number,
        "day_number":         payload.day_number,
        "rot_date":           payload.rot_date,
        "rot_time":           payload.rot_time,
        "plane_registration": payload.plane_registration,
        "pilot":              payload.pilot,
        "chef_avion":         payload.chef_avion,
        "participants": [
            {
                "afifly_name": p.afifly_name,
                "level":       p.level,
                "weight":      p.weight,
                "jump_type":   p.jump_type,
                "group_id":    p.group_id,
            }
            for p in payload.participants
        ],
    }
    return _persist_rot(data, db)


@router.get("", response_model=list[RotResponse])
def list_rots(db: Session = Depends(get_db)):
    """Retourne toutes les rotations, de la plus récente à la plus ancienne."""
    return db.query(Rot).order_by(Rot.rot_date.desc(), Rot.rot_time.desc()).all()


@router.get("/{rot_id}", response_model=RotResponse)
def get_rot(rot_id: int, db: Session = Depends(get_db)):
    """Retourne une rotation."""
    rot = db.query(Rot).filter(Rot.id == rot_id).first()
    if not rot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rot introuvable.")
    return rot
