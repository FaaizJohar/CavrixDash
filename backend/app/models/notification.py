from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Notification(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), default="info", index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(300), default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    meta: Mapped[str] = mapped_column(Text, default="{}")


class Announcement(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "announcements"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    audience: Mapped[str] = mapped_column(String(40), default="all")  # all|users|admins
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    starts_at: Mapped[str] = mapped_column(String(40), default="")
    ends_at: Mapped[str] = mapped_column(String(40), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(36), default="")
