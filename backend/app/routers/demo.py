"""'Load Hackathon Demo' -- creates a fresh inspection from one of the 3
canned scenarios with evidence already attached, but NOT yet OCR'd or
analyzed, so the officer walks it through the real pipeline (Run OCR ->
Analyze Compliance) rather than seeing a pre-baked result appear by magic.
"""
import datetime as dt
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..routers.inspections import find_or_create_product
from ..seed_data.demo_scenarios import get_scenario
from ..services.audit import record as audit_record
from ..services.demo.assets_generator import generate_all_demo_assets
from ..services.storage import get_storage
from ..services.view_models import build_inspection_out

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/load", response_model=schemas.InspectionOut, status_code=201)
def load_demo(
    payload: schemas.DemoLoadRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        scenario = get_scenario(payload.scenario)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    generate_all_demo_assets()  # idempotent; guarantees the PNGs exist

    product = find_or_create_product(db, scenario.product_name, scenario.brand, scenario.category)

    inspection = models.Inspection(
        reference_code=(
            f"MC-{dt.datetime.utcnow():%Y%m%d}-DEMO{dt.datetime.utcnow():%H%M%S}"
        ),
        product_id=product.id,
        inspector_id=current_user.id,
        batch_lot=scenario.batch_lot,
        manufacturer_name=scenario.manufacturer_name,
        supply_type=scenario.supply_type,
        inspection_location=scenario.inspection_location,
        inspection_date=dt.datetime.utcnow(),
        listing_url=scenario.listing_url,
        status=models.InspectionStatus.DRAFT,
        demo_scenario=scenario.key,
    )
    db.add(inspection)
    db.flush()

    storage = get_storage()
    for spec in scenario.images:
        asset_path = os.path.join(settings.DEMO_ASSETS_ROOT, scenario.key, f"{spec.slug}.png")
        with open(asset_path, "rb") as f:
            data = f.read()
        rel_path = storage.save(f"inspections/{inspection.id}", f"{spec.slug}.png", data)
        db.add(
            models.Evidence(
                inspection_id=inspection.id,
                image_type=spec.image_type,
                file_path=rel_path,
                original_filename=f"{spec.slug}.png",
                content_type="image/png",
                file_size_bytes=len(data),
                uploaded_by=current_user.id,
            )
        )

    inspection.status = models.InspectionStatus.EVIDENCE_UPLOADED

    audit_record(
        db,
        current_user,
        "INSPECTION_CREATED",
        "Inspection",
        inspection.id,
        description=(
            f"Inspection {inspection.reference_code} created via Load Hackathon Demo "
            f"(scenario={scenario.key})."
        ),
    )
    db.commit()

    full = (
        db.query(models.Inspection)
        .options(
            joinedload(models.Inspection.product),
            joinedload(models.Inspection.inspector),
            joinedload(models.Inspection.evidence_items),
            joinedload(models.Inspection.declarations),
        )
        .filter(models.Inspection.id == inspection.id)
        .first()
    )
    return build_inspection_out(full)
