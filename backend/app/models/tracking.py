from __future__ import annotations

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class TaskClick(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "task_clicks"

    click_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    offer_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    ip: Mapped[str] = mapped_column(String(45), default="")
    user_agent: Mapped[str] = mapped_column(Text, default="")
    device_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    redirect_url: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending | approved | rejected | reversed | expired | held
    external_tx_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    reward_offered: Mapped[float] = mapped_column(Float, default=0.0)
    country: Mapped[str] = mapped_column(String(8), default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")


class Conversion(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "conversions"
    __table_args__ = (
        # Replay/idempotency guard enforced at the database layer so two
        # concurrent postbacks can never both credit the same conversion.
        # A unique index (rather than a table constraint) so it is created
        # identically on SQLite and Postgres.
        Index("uq_conversions_provider_conversion", "provider_id", "conversion_id", unique=True),
    )

    click_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    offer_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    conversion_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    external_tx_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    ip: Mapped[str] = mapped_column(String(45), default="")
    device_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending | approved | rejected | reversed | held | expired
    reward_amount: Mapped[float] = mapped_column(Float, default=0.0)
    payout_amount: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    reviewed_by: Mapped[str] = mapped_column(String(36), default="")
    reviewed_at: Mapped[str] = mapped_column(String(40), default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")


class Postback(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "postbacks"

    provider_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    external_conversion_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    raw_payload: Mapped[str] = mapped_column(Text, default="")
    signature_valid: Mapped[str] = mapped_column(String(10), default="pending")  # valid|invalid|unknown
    nonce: Mapped[str] = mapped_column(String(120), default="")
    received_at: Mapped[str] = mapped_column(String(40), default="")
    processed: Mapped[str] = mapped_column(String(10), default="pending")  # pending|processed|duplicate|rejected
    result: Mapped[str] = mapped_column(Text, default="")
    source_ip: Mapped[str] = mapped_column(String(45), default="")


class Reversal(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "reversals"

    conversion_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(200), default="")
    raw_payload: Mapped[str] = mapped_column(Text, default="")
    reversed_by: Mapped[str] = mapped_column(String(20), default="provider")  # provider|admin|system
    credited_back: Mapped[str] = mapped_column(String(10), default="pending")
