"""Audit trail retrieval. Viewable by any authenticated role in this
prototype -- see CLAUDE.md/README for the RBAC-scoping note."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[schemas.AuditEventOut])
def list_audit_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.AuditEvent).options(joinedload(models.AuditEvent.user))
    if entity_type:
        query = query.filter(models.AuditEvent.entity_type == entity_type)
    if action:
        query = query.filter(models.AuditEvent.action == action)

    rows = query.order_by(models.AuditEvent.timestamp.desc()).offset(skip).limit(limit).all()
    return [
        schemas.AuditEventOut(
            id=r.id,
            user_id=r.user_id,
            user_name=r.user.full_name if r.user else None,
            role_name=r.role_name,
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            description=r.description,
            before=r.before,
            after=r.after,
            timestamp=r.timestamp,
        )
        for r in rows
    ]
