from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class FraudEvent(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "fraud_events"

    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    related_id: Mapped[str] = mapped_column(String(36), default="", index=True)  # click/conversion id
    severity: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    ip: Mapped[str] = mapped_column(String(45), default="", index=True)
    device_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    action: Mapped[str] = mapped_column(String(30), default="")  # allow|hold|verify|suspend|ban|reverse|review
    handled: Mapped[str] = mapped_column(String(10), default="pending")  # pending|reviewed
    meta: Mapped[str] = mapped_column(Text, default="{}")


class FraudRule(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "fraud_rules"

    key: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(160), default="")
    value: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[str] = mapped_column(String(5), default="true")
    description: Mapped[str] = mapped_column(Text, default="")
