from __future__ import annotations

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Session(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(120), default="")
    ip: Mapped[str] = mapped_column(String(45), default="")
    user_agent: Mapped[str] = mapped_column(String(400), default="")
    expires_at: Mapped[str] = mapped_column(String(40), default="")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[str] = mapped_column(String(40), default="")

    def is_active(self) -> bool:
        try:
            from datetime import datetime

            exp = datetime.fromisoformat(self.expires_at)
            return (not self.revoked) and exp > utcnow()
        except Exception:
            return False
