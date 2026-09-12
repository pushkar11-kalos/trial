"""Inspection create / list / retrieve / update / finalize."""
import datetime as dt
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.audit import record as audit_record
from ..services.view_models import build_inspection_out, build_list_item

router = APIRouter(prefix="/api", tags=["inspections"])


def _load_full(db: Session, inspection_id: int) -> models.Inspection:
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


def find_or_create_product(
    db: Session, name: str, brand: Optional[str], category: Optional[str]
) -> models.Product:
    query = db.query(models.Product).filter(models.Product.name.ilike(name))
    if brand:
        query = query.filter(models.Product.brand.ilike(brand))
    existing = query.first()
    if existing:
        if category and not existing.category:
            existing.category = category
        return existing
    product = models.Product(name=name, brand=brand, category=category)
    db.add(product)
    db.flush()
    return product


def generate_reference_code(prefix: str = "") -> str:
    tag = f"{prefix.upper()[:3]}" if prefix else uuid.uuid4().hex[:3].upper()
    return f"MC-{dt.datetime.utcnow():%Y%m%d}-{tag}{uuid.uuid4().hex[:4].upper()}"


@router.post("/inspections", response_model=schemas.InspectionOut, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: schemas.InspectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    product = find_or_create_product(db, payload.product_name, payload.brand, payload.category)
    inspection = models.Inspection(
        reference_code=generate_reference_code(),
        product_id=product.id,
        inspector_id=current_user.id,
        batch_lot=payload.batch_lot,
        manufacturer_name=payload.manufacturer_name,
        supply_type=payload.supply_type,
        inspection_location=payload.inspection_location,
        inspection_date=payload.inspection_date or dt.datetime.utcnow(),
        listing_url=payload.listing_url,
        status=models.InspectionStatus.DRAFT,
    )
    db.add(inspection)
    db.flush()

    audit_record(
        db,
        current_user,
        "INSPECTION_CREATED",
        "Inspection",
        inspection.id,
        description=f"Inspection {inspection.reference_code} created for {product.name}.",
    )
    db.commit()
    return build_inspection_out(_load_full(db, inspection.id))


@router.get("/inspections", response_model=List[schemas.InspectionListItem])
def list_inspections(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    limit: int = 50,
):
    rows = (
        db.query(models.Inspection)
        .options(joinedload(models.Inspection.product), joinedload(models.Inspection.inspector))
        .order_by(models.Inspection.created_at.desc())
        .limit(limit)
        .all()
    )
    return [build_list_item(r) for r in rows]


@router.get("/inspections/{inspection_id}", response_model=schemas.InspectionOut)
def get_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return build_inspection_out(_load_full(db, inspection_id))


@router.patch("/inspections/{inspection_id}", response_model=schemas.InspectionOut)
def update_inspection(
    inspection_id: int,
    payload: schemas.InspectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    insp = _load_full(db, inspection_id)
    if insp.status == models.InspectionStatus.FINALIZED:
        raise HTTPException(status_code=400, detail="Finalized inspections cannot be edited.")

    before = {
        "batch_lot": insp.batch_lot,
        "manufacturer_name": insp.manufacturer_name,
        "supply_type": insp.supply_type.value,
        "inspection_location": insp.inspection_location,
    }

    data = payload.model_dump(exclude_unset=True)
    if any(k in data for k in ("product_name", "brand", "category")):
        insp.product.name = data.get("product_name", insp.product.name)
        insp.product.brand = data.get("brand", insp.product.brand)
        insp.product.category = data.get("category", insp.product.category)

    for field in (
        "batch_lot",
        "manufacturer_name",
        "supply_type",
        "inspection_location",
        "inspection_date",
        "listing_url",
    ):
        if field in data:
            setattr(insp, field, data[field])

    insp.updated_at = dt.datetime.utcnow()

    audit_record(
        db,
        current_user,
        "INSPECTION_UPDATED",
        "Inspection",
        insp.id,
        description="Inspection details updated.",
        before=before,
        after=data,
    )
    db.commit()
    return build_inspection_out(_load_full(db, inspection_id))


@router.post("/inspections/{inspection_id}/finalize", response_model=schemas.InspectionOut)
def finalize_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    insp = _load_full(db, inspection_id)
    if not insp.compliance_runs:
        raise HTTPException(status_code=400, detail="Run compliance analysis before finalizing.")
    if insp.status == models.InspectionStatus.FINALIZED:
        raise HTTPException(status_code=400, detail="Inspection is already finalized.")

    insp.status = models.InspectionStatus.FINALIZED
    insp.finalized_at = dt.datetime.utcnow()
    insp.updated_at = insp.finalized_at

    audit_record(
        db,
        current_user,
        "INSPECTION_FINALIZED",
        "Inspection",
        insp.id,
        description=f"Inspection {insp.reference_code} finalized.",
    )
    db.commit()
    return build_inspection_out(_load_full(db, inspection_id))
