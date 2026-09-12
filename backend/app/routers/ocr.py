"""OCR execution + retrieval."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services import pipeline
from ..services.storage import get_storage

router = APIRouter(prefix="/api", tags=["ocr"])


def _load_for_ocr(db: Session, inspection_id: int) -> models.Inspection:
    insp = (
        db.query(models.Inspection)
        .options(
            joinedload(models.Inspection.product),
            joinedload(models.Inspection.evidence_items),
            joinedload(models.Inspection.declarations),
        )
        .filter(models.Inspection.id == inspection_id)
        .first()
    )
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if not insp.evidence_items:
        raise HTTPException(status_code=400, detail="Upload evidence before running OCR.")
    return insp


@router.post("/inspections/{inspection_id}/ocr")
def run_ocr(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    insp = _load_for_ocr(db, inspection_id)
    result = pipeline.process_ocr_and_extraction(db, insp, get_storage(), current_user)
    db.commit()
    return {
        "ocr_results": [schemas.OCRResultOut.model_validate(r) for r in result["ocr_results"]],
        "declarations": [schemas.DeclarationOut.model_validate(d) for d in result["declarations"]],
    }


@router.get("/inspections/{inspection_id}/ocr", response_model=list[schemas.OCRResultOut])
def get_ocr_results(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    evidence_ids = [
        e.id for e in db.query(models.Evidence.id).filter(models.Evidence.inspection_id == inspection_id).all()
    ]
    if not evidence_ids:
        return []
    results = (
        db.query(models.OCRResult)
        .filter(models.OCRResult.evidence_id.in_(evidence_ids))
        .order_by(models.OCRResult.processed_at.desc())
        .all()
    )
    latest_by_evidence: dict[int, models.OCRResult] = {}
    for r in results:
        latest_by_evidence.setdefault(r.evidence_id, r)
    return list(latest_by_evidence.values())
