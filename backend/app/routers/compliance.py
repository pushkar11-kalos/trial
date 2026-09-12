"""Compliance analysis: run + retrieve."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services import pipeline
from ..services.view_models import build_compliance_run_out, build_finding_out

router = APIRouter(prefix="/api", tags=["compliance"])


def _load_for_compliance(db: Session, inspection_id: int) -> models.Inspection:
    insp = (
        db.query(models.Inspection)
        .options(joinedload(models.Inspection.product), joinedload(models.Inspection.declarations))
        .filter(models.Inspection.id == inspection_id)
        .first()
    )
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if not insp.declarations:
        raise HTTPException(
            status_code=400, detail="Run OCR and extract declarations before analyzing compliance."
        )
    return insp


def _load_run_full(db: Session, run_id: int) -> models.ComplianceRun:
    return (
        db.query(models.ComplianceRun)
        .options(
            joinedload(models.ComplianceRun.findings).joinedload(models.Finding.officer_decisions),
            joinedload(models.ComplianceRun.rule_pack),
        )
        .filter(models.ComplianceRun.id == run_id)
        .first()
    )


@router.post("/inspections/{inspection_id}/compliance/run", response_model=schemas.ComplianceRunOut)
def run_compliance_analysis(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    insp = _load_for_compliance(db, inspection_id)
    try:
        run = pipeline.run_compliance(db, insp, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    return build_compliance_run_out(_load_run_full(db, run.id))


@router.get("/inspections/{inspection_id}/compliance", response_model=schemas.ComplianceRunOut)
def get_latest_compliance(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    run = (
        db.query(models.ComplianceRun)
        .filter(models.ComplianceRun.inspection_id == inspection_id)
        .order_by(models.ComplianceRun.run_at.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="No compliance analysis has been run yet.")
    return build_compliance_run_out(_load_run_full(db, run.id))


@router.get("/inspections/{inspection_id}/compliance/findings", response_model=list[schemas.FindingOut])
def get_latest_findings(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    run = (
        db.query(models.ComplianceRun)
        .options(joinedload(models.ComplianceRun.findings).joinedload(models.Finding.officer_decisions))
        .filter(models.ComplianceRun.inspection_id == inspection_id)
        .order_by(models.ComplianceRun.run_at.desc())
        .first()
    )
    if not run:
        return []
    return [build_finding_out(f) for f in run.findings]
