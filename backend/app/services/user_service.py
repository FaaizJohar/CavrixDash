from __future__ import annotations

import json
import secrets
import string

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.server import UserServer
from app.models.user import Role, User


def _referral_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        return code


def create_user(
    db: Session,
    *,
    email: str,
    username: str,
    password: str,
    display_name: str = "",
    referral_code: str = "",
) -> User:
    email = email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise ConflictError("An account with this email already exists.", code="EMAIL_TAKEN")
    if db.query(User).filter(User.username == username).first():
        raise ConflictError("This username is already taken.", code="USERNAME_TAKEN")

    user = User(
        email=email,
        username=username,
        display_name=display_name or username,
        password_hash=hash_password(password),
        referral_code=_referral_code(),
        invited_by=None,
    )
    role = db.query(Role).filter(Role.name == "user").first()
    if role:
        user.roles = [role]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_by_referral_code(db: Session, code: str) -> User | None:
    return db.query(User).filter(User.referral_code == code.upper()).first()


def find(db: Session, term: str) -> User | None:
    term = term.strip()
    user = get_by_email(db, term)
    if user:
        return user
    return get_by_username(db, term)


def list_users(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str = "",
    status: str = "",
    sort: str = "created_at",
) -> tuple[list[User], int]:
    q = db.query(User)
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(User.email.ilike(like), User.username.ilike(like), User.display_name.ilike(like))
        )
    if status:
        q = q.filter(User.status == status)
    order_col = getattr(User, sort, User.created_at)
    q = q.order_by(order_col.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def require_active(user: User) -> None:
    if user.status == "banned":
        raise NotFoundError("This account has been banned.", code="ACCOUNT_BANNED")
    if user.status == "suspended":
        raise NotFoundError("This account is suspended.", code="ACCOUNT_SUSPENDED")


def to_me(db: Session, user: User) -> dict:
    """Serialize a User into the UserMe shape (roles as names + computed counts)."""
    from app.services import settings_service as settings

    active_servers = (
        db.query(UserServer)
        .filter(UserServer.user_id == user.id, UserServer.status.in_(["running", "starting", "creating"]))
        .count()
    )
    server_limit = int(settings.get_value(db, "minecraft.max_servers_per_user", 3))
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "referral_code": user.referral_code,
        "email_verified": user.email_verified,
        "twofa_enabled": user.twofa_enabled,
        "status": user.status,
        "roles": [r.name for r in user.roles],
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "cvx_balance": user.cvx_balance,
        "cvx_lifetime_earned": user.cvx_lifetime_earned,
        "cvx_lifetime_spent": user.cvx_lifetime_spent,
        "tasks_completed": user.tasks_completed,
        "conversions_approved": user.conversions_approved,
        "conversions_pending": user.conversions_pending,
        "active_servers": active_servers,
        "server_limit": server_limit,
        "is_super_admin": user.is_super_admin,
        "is_admin": user.is_admin,
    }
