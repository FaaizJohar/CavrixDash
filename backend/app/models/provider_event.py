from __future__ import annotations

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ProviderEvent(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "provider_events"

    provider_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    request_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    raw_payload: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="received")
    result: Mapped[str] = mapped_column(Text, default="")
    source_ip: Mapped[str] = mapped_column(String(45), default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")


class OfferSession(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "offer_sessions"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    offer_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    click_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    session_token: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    ip: Mapped[str] = mapped_column(String(45), default="")
    device_id: Mapped[str] = mapped_column(String(64), default="")
    converted_at: Mapped[str] = mapped_column(String(40), default="")
    conversion_id: Mapped[str] = mapped_column(String(36), default="", index=True)
