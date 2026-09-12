"""Report generation: PDF + editable DOCX, from the same context builder."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services import pipeline
from ..services.storage import get_storage

router = APIRouter(prefix="/api", tags=["reports"])


def _load_full_for_report(db: Session, inspection_id: int) -> models.Inspection:
    insp = (
        db.query(models.Inspection)
        .options(
            joinedload(models.Inspection.product),
            joinedload(models.Inspection.inspector),
            joinedload(models.Inspection.evidence_items),
            joinedload(models.Inspection.declarations),
            joinedload(models.Inspection.compliance_runs)
            .joinedload(models.ComplianceRun.findings)
            .joinedload(models.Finding.officer_decisions),
            joinedload(models.Inspection.compliance_runs).joinedload(models.ComplianceRun.rule_pack),
        )
        .filter(models.Inspection.id == inspection_id)
        .first()
    )
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return insp


@router.post("/inspections/{inspection_id}/reports/pdf", response_model=schemas.ReportOut)
def generate_pdf(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    insp = _load_full_for_report(db, inspection_id)
    report = pipeline.generate_report(db, insp, models.ReportType.PDF, get_storage(), current_user)
    db.commit()
    db.refresh(report)
    return report


@router.post("/inspections/{inspection_id}/reports/docx", response_model=schemas.ReportOut)
def generate_docx(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    insp = _load_full_for_report(db, inspection_id)
    report = pipeline.generate_report(db, insp, models.ReportType.DOCX, get_storage(), current_user)
    db.commit()
    db.refresh(report)
    return report


@router.get("/inspections/{inspection_id}/reports", response_model=list[schemas.ReportOut])
def list_reports(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Report)
        .filter(models.Report.inspection_id == inspection_id)
        .order_by(models.Report.generated_at.desc())
        .all()
    )
