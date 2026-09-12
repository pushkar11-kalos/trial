"""Repository search: the filterable inspection history view."""
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, contains_eager, joinedload

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..services.view_models import build_list_item

router = APIRouter(prefix="/api", tags=["repository"])


@router.get("/repository")
def search_repository(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    status_filter: Optional[models.InspectionStatus] = Query(None, alias="status"),
    result_filter: Optional[models.OverallResult] = Query(None, alias="result"),
    category: Optional[str] = None,
    supply_type: Optional[models.SupplyType] = None,
    location: Optional[str] = None,
    severity: Optional[models.Severity] = None,
    q: Optional[str] = None,
    date_from: Optional[dt.datetime] = None,
    date_to: Optional[dt.datetime] = None,
    skip: int = 0,
    limit: int = 50,
):
    query = (
        db.query(models.Inspection)
        .join(models.Product, models.Inspection.product_id == models.Product.id)
        .options(contains_eager(models.Inspection.product), joinedload(models.Inspection.inspector))
    )

    if status_filter:
        query = query.filter(models.Inspection.status == status_filter)
    if result_filter:
        query = query.filter(models.Inspection.overall_result == result_filter)
    if supply_type:
        query = query.filter(models.Inspection.supply_type == supply_type)
    if location:
        query = query.filter(models.Inspection.inspection_location.ilike(f"%{location}%"))
    if date_from:
        query = query.filter(models.Inspection.inspection_date >= date_from)
    if date_to:
        query = query.filter(models.Inspection.inspection_date <= date_to)
    if category:
        query = query.filter(models.Product.category == category)
    if q:
        query = query.filter(
            or_(
                models.Inspection.reference_code.ilike(f"%{q}%"),
                models.Product.name.ilike(f"%{q}%"),
                models.Product.brand.ilike(f"%{q}%"),
                models.Inspection.batch_lot.ilike(f"%{q}%"),
            )
        )

    rows = query.order_by(models.Inspection.created_at.desc()).all()

    if severity:
        rows = [
            insp
            for insp in rows
            if insp.compliance_runs and any(f.severity == severity for f in insp.compliance_runs[-1].findings)
        ]

    total = len(rows)
    page = rows[skip : skip + limit]
    return {"items": [build_list_item(r) for r in page], "total": total}
