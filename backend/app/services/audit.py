"""
Audit logging helper. Adds an AuditEvent to the current session WITHOUT
committing -- callers commit once, atomically, alongside the actual change
being logged, so an audit row never exists for a change that was rolled
back.
"""
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models


def record(
    db: Session,
    user: Optional[models.User],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    description: str = "",
    before: Optional[Any] = None,
    after: Optional[Any] = None,
) -> models.AuditEvent:
    event = models.AuditEvent(
        user_id=user.id if user else None,
        role_name=user.role_value if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        description=description,
        before=before,
        after=after,
    )
    db.add(event)
    return event
