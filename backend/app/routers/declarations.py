"""Declaration retrieval + manual correction."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.audit import record as audit_record

router = APIRouter(prefix="/api", tags=["declarations"])


@router.get("/inspections/{inspection_id}/declarations", response_model=list[schemas.DeclarationOut])
def list_declarations(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Declaration).filter(models.Declaration.inspection_id == inspection_id).all()


@router.patch("/declarations/{declaration_id}", response_model=schemas.DeclarationOut)
def update_declaration(
    declaration_id: int,
    payload: schemas.DeclarationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    decl = db.query(models.Declaration).filter(models.Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Declaration not found")

    before_value = decl.value
    decl.value = payload.value
    decl.confidence = 100.0
    decl.extraction_method = "manual"
    decl.is_manually_edited = True
    decl.updated_by = current_user.id

    audit_record(
        db,
        current_user,
        "OCR_EDITED",
        "Declaration",
        decl.id,
        description=f"{decl.field_key.value} corrected manually.",
        before={"value": before_value},
        after={"value": payload.value},
    )
    db.commit()
    db.refresh(decl)
    return decl
