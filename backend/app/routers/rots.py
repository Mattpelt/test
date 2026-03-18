import os
import tempfile

import pdfplumber
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rot import Rot
from app.models.rot_participant import RotParticipant
from app.models.user import User
from app.schemas.rot import RotResponse
from app.services.pdf_parser import parse_afifly_pdf

router = APIRouter(prefix="/rots", tags=["Rotations"])


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

            unique_linewidths = sorted(set(
                round(e.get("linewidth", 0), 2)
                for e in page.edges
                if e.get("orientation") == "h"
            ))

            return {
                "num_tables": len(tables_info),
                "tables": tables_info,
                "num_rects": len(rects_info),
                "rects": rects_info,
                "horizontal_edge_linewidths": unique_linewidths,
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

    # Créer le rot
    rot = Rot(
        rot_number         = data["rot_number"],
        day_number         = data.get("day_number"),
        rot_date           = data["rot_date"],
        rot_time           = data["rot_time"],
        plane_registration = data.get("plane_registration"),
        pilot              = data.get("pilot"),
        chef_avion         = data.get("chef_avion"),
        source_pdf_path    = tmp_path,
        parse_status       = "OK",
    )
    db.add(rot)
    db.flush()  # obtenir rot.id avant les participants

    # Créer les participants + tenter le matching avec les comptes existants
    matched = 0
    for p in data.get("participants", []):
        user = (
            db.query(User)
            .filter(User.afifly_name == p["afifly_name"], User.is_active == True)
            .first()
        )
        if user:
            matched += 1

        participant = RotParticipant(
            rot_id      = rot.id,
            user_id     = user.id if user else None,
            afifly_name = p["afifly_name"],
            level       = p.get("level"),
            weight      = p.get("weight"),
            jump_type   = p.get("jump_type"),
            group_id    = p.get("group_id", 1),
        )
        db.add(participant)

    db.commit()
    db.refresh(rot)

    total = len(data.get("participants", []))
    print(f"Rot n°{rot.rot_number} enregistré — {total} participants, {matched} matchés.")

    return rot


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
