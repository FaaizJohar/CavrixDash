from __future__ import annotations

from typing import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.core.database import get_db
from app.models.user import User
from app.services import user_service


def get_client_meta(request: Request) -> dict[str, str]:
    ip = request.client.host if request.client else ""
    if xff := request.headers.get("x-forwarded-for"):
        ip = xff.split(",")[0].strip()
    return {
        "ip": ip or "",
        "user_agent": request.headers.get("user-agent", ""),
        "device_id": request.headers.get("x-device-id", ""),
        "device_name": request.headers.get("x-device-name", ""),
    }


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    auth = request.headers.get("authorization", "")
    token = None
    if auth.lower().startswith("bearer "):
        token = auth[7:]
    if not token and request.headers.get("x-access-token"):
        token = request.headers["x-access-token"]
    if not token:
        raise UnauthorizedError("Not authenticated.", code="NOT_AUTHENTICATED")
    try:
        payload = decode_token(token)
    except Exception:
        raise UnauthorizedError("Invalid or expired token.", code="TOKEN_EXPIRED")
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type.", code="TOKEN_EXPIRED")
    user = user_service.get_by_id(db, payload["sub"])
    if not user:
        raise UnauthorizedError("Account no longer exists.", code="NOT_AUTHENTICATED")
    user_service.require_active(user)
    return user


def require_roles(*roles: str) -> Callable:
    def dep(user: User = Depends(get_current_user)) -> User:
        if not any(user.has_role(r) for r in roles):
            raise ForbiddenError(
                "You do not have permission to perform this action.",
                code="FORBIDDEN",
            )
        return user

    return dep


require_super_admin = require_roles("super_admin")
require_admin = require_roles("super_admin", "admin")
require_staff = require_roles("super_admin", "admin", "support", "moderator")
require_finance = require_roles("super_admin", "admin", "finance_admin")
require_infra = require_roles("super_admin", "admin", "infra_admin")
require_dashboard = require_roles("super_admin", "admin", "finance_admin", "infra_admin")


def verify_step_up(request: Request, user: User) -> None:
    """Validates a fresh step-up token bound to the current user.

    Call from inside a handler when only part of the request is sensitive
    (e.g. role/CVX changes on an otherwise permissive user-update endpoint).
    """
    token = request.headers.get("x-step-up-token", "")
    if not token:
        raise ForbiddenError(
            "Re-enter your password to confirm this action.", code="STEP_UP_REQUIRED"
        )
    try:
        payload = decode_token(token)
    except Exception:
        raise ForbiddenError(
            "Step-up verification expired. Please confirm again.", code="STEP_UP_REQUIRED"
        )
    if payload.get("type") != "step_up" or payload.get("sub") != user.id:
        raise ForbiddenError(
            "Step-up verification invalid. Please confirm again.", code="STEP_UP_REQUIRED"
        )


def require_step_up(
    request: Request, user: User = Depends(get_current_user)
) -> User:
    verify_step_up(request, user)
    return user
