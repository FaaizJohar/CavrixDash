from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.security import verify_password, hash_password
from app.models.user import User
from app.schemas import auth as s
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=s.UserMe)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return s.UserMe.model_validate(user_service.to_me(db, user))


@router.patch("/me", response_model=s.UserMe)
def update_me(payload: s.UpdateProfileRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.current_password is None and payload.password:
        raise AppError("Current password is required to change your password.", code="CURRENT_PASSWORD_REQUIRED")
    if payload.password:
        if not verify_password(payload.current_password or "", user.password_hash):
            raise AppError("Current password is incorrect.", code="INVALID_CREDENTIALS")
        user.password_hash = hash_password(payload.password)
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    db.commit()
    db.refresh(user)
    return s.UserMe.model_validate(user_service.to_me(db, user))


@router.post("/me/avatar", response_model=s.UserMe)
def set_avatar(payload: s.UpdateProfileRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not payload.avatar_url:
        raise AppError("avatar_url is required.", code="VALIDATION_ERROR")
    user.avatar_url = payload.avatar_url
    db.commit()
    db.refresh(user)
    return s.UserMe.model_validate(user_service.to_me(db, user))


@router.post("/me/delete")
def request_deletion(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.status = "suspended"
    db.commit()
    return {"message": "Deletion requested. Our team will process it."}
