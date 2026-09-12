"""Rule pack / rule retrieval, plus admin-only metadata editing.

Ordinary inspectors cannot reach the PATCH endpoint at all (RBAC via
require_roles) -- rule *structure* (validation_logic, rule_code, category)
is intentionally not editable via this API in this prototype; only
descriptive metadata and activation status are. See CLAUDE.md/README for
why full dynamic rule authoring is out of scope here.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..services.audit import record as audit_record

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("/packs", response_model=list[schemas.RulePackOut])
def list_rule_packs(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    return (
        db.query(models.RulePack)
        .options(joinedload(models.RulePack.rules))
        .order_by(models.RulePack.created_at.desc())
        .all()
    )


@router.get("/packs/active", response_model=schemas.RulePackOut)
def get_active_rule_pack(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    pack = (
        db.query(models.RulePack)
        .options(joinedload(models.RulePack.rules))
        .filter(models.RulePack.is_active.is_(True))
        .first()
    )
    if not pack:
        raise HTTPException(status_code=404, detail="No active rule pack configured.")
    return pack


@router.get("/packs/{pack_id}", response_model=schemas.RulePackOut)
def get_rule_pack(
    pack_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    pack = (
        db.query(models.RulePack)
        .options(joinedload(models.RulePack.rules))
        .filter(models.RulePack.id == pack_id)
        .first()
    )
    if not pack:
        raise HTTPException(status_code=404, detail="Rule pack not found")
    return pack


@router.patch("/{rule_id}", response_model=schemas.RuleOut)
def update_rule(
    rule_id: int,
    payload: schemas.RuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(models.RoleName.ADMINISTRATOR.value)),
):
    rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    before = {"name": rule.name, "severity": rule.severity.value, "is_active": rule.is_active}
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(rule, field, value)

    audit_record(
        db,
        current_user,
        "RULE_UPDATED",
        "Rule",
        rule.id,
        description=f"{rule.rule_code} updated by administrator.",
        before=before,
        after=data,
    )
    db.commit()
    db.refresh(rule)
    return rule
