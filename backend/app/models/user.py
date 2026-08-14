from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, utcnow

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")


class Role(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, lazy="selectin"
    )


class User(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), default="")
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    referral_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    twofa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    twofa_secret: Mapped[str] = mapped_column(String(128), default="")
    backup_codes: Mapped[str] = mapped_column(String(2000), default="")  # JSON list (hashed)
    last_login_at: Mapped[str] = mapped_column(String(40), default="")
    last_login_ip: Mapped[str] = mapped_column(String(45), default="")

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|suspended|banned
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    referral_cvx_earned: Mapped[float] = mapped_column(Float, default=0.0)

    cvx_balance: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    cvx_lifetime_earned: Mapped[float] = mapped_column(Float, default=0.0)
    cvx_lifetime_spent: Mapped[float] = mapped_column(Float, default=0.0)

    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    conversions_approved: Mapped[int] = mapped_column(Integer, default=0)
    conversions_pending: Mapped[int] = mapped_column(Integer, default=0)

    invited_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    panel_user_id: Mapped[str] = mapped_column(String(36), default="")
    meta: Mapped[str] = mapped_column(String(4000), default="{}")

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, lazy="selectin", backref="users"
    )

    def has_role(self, role: str) -> bool:
        return any(r.name == role for r in self.roles)

    @property
    def is_super_admin(self) -> bool:
        return self.has_role("super_admin")

    @property
    def is_admin(self) -> bool:
        return self.is_super_admin or self.has_role("admin")

    @property
    def is_finance_admin(self) -> bool:
        return self.is_super_admin or self.is_admin or self.has_role("finance_admin")

    @property
    def is_infra_admin(self) -> bool:
        return self.is_super_admin or self.is_admin or self.has_role("infra_admin")

    @property
    def requires_mandatory_mfa(self) -> bool:
        return self.is_super_admin or self.has_role("finance_admin") or self.has_role("infra_admin")
