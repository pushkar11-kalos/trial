"""Officer review: confirm / dismiss / mark-for-review a Finding.

A decision is always a new OfficerDecision row -- the Finding itself
(the machine_result) is never mutated. See app/services/pipeline.py.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services import pipeline
from ..services.view_models import build_finding_out

router = APIRouter(prefix="/api", tags=["review"])


@router.post("/findings/{finding_id}/review", response_model=schemas.FindingOut)
def review_finding(
    finding_id: int,
    payload: schemas.OfficerDecisionIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    finding = (
        db.query(models.Finding)
        .options(joinedload(models.Finding.compliance_run).joinedload(models.ComplianceRun.inspection))
        .filter(models.Finding.id == finding_id)
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    pipeline.record_officer_decision(db, finding, payload.decision, payload.note, current_user)
    db.commit()

    full = (
        db.query(models.Finding)
        .options(joinedload(models.Finding.officer_decisions))
        .filter(models.Finding.id == finding_id)
        .first()
    )
    return build_finding_out(full)
