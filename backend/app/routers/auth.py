"""Authentication: JSON login (not an OAuth2 form) + current user. See
CLAUDE.md for why HTTPBearer is used instead of OAuth2PasswordBearer."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..security import create_access_token, verify_password
from ..services.audit import record as audit_record

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token(subject=str(user.id), role=user.role_value)
    audit_record(db, user, "LOGIN", "User", user.id, description=f"{user.email} logged in.")
    db.commit()

    return schemas.TokenResponse(access_token=token, user=schemas.UserOut.from_orm_user(user))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return schemas.UserOut.from_orm_user(current_user)
