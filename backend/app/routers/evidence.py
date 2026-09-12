"""Evidence upload / list / delete."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..services.audit import record as audit_record
from ..services.storage import get_storage

router = APIRouter(prefix="/api", tags=["evidence"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post(
    "/inspections/{inspection_id}/evidence",
    response_model=schemas.EvidenceOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence(
    inspection_id: int,
    image_type: models.EvidenceType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inspection = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if inspection.status == models.InspectionStatus.FINALIZED:
        raise HTTPException(status_code=400, detail="Cannot add evidence to a finalized inspection.")
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit.")

    storage = get_storage()
    rel_path = storage.save(f"inspections/{inspection_id}", file.filename or "upload", data)

    evidence = models.Evidence(
        inspection_id=inspection_id,
        image_type=image_type,
        file_path=rel_path,
        original_filename=file.filename,
        content_type=file.content_type,
        file_size_bytes=len(data),
        uploaded_by=current_user.id,
    )
    db.add(evidence)
    db.flush()

    if inspection.status == models.InspectionStatus.DRAFT:
        inspection.status = models.InspectionStatus.EVIDENCE_UPLOADED

    audit_record(
        db,
        current_user,
        "IMAGE_UPLOADED",
        "Evidence",
        evidence.id,
        description=f"{image_type.value} image uploaded to inspection {inspection.reference_code}.",
    )
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/inspections/{inspection_id}/evidence", response_model=list[schemas.EvidenceOut])
def list_evidence(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Evidence)
        .filter(models.Evidence.inspection_id == inspection_id)
        .order_by(models.Evidence.uploaded_at)
        .all()
    )


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    storage = get_storage()
    storage.delete(evidence.file_path)
    db.delete(evidence)
    audit_record(db, current_user, "EVIDENCE_DELETED", "Evidence", evidence_id, description="Evidence deleted.")
    db.commit()
    return None
