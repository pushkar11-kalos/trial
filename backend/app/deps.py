"""
Shared FastAPI dependencies: DB session passthrough, current-user resolution,
and role-based access control.
"""
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if creds is None or not creds.credentials:
        raise _CREDENTIALS_EXCEPTION
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise _CREDENTIALS_EXCEPTION

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


def require_roles(*roles: Iterable[str]):
    """
    Usage: Depends(require_roles(RoleName.ADMINISTRATOR.value))
    or Depends(require_roles(RoleName.ADMINISTRATOR.value, RoleName.SUPERVISOR.value))
    """
    allowed = set(roles)

    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role_value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return dependency
