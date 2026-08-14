from __future__ import annotations

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class CvxLedger(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "cvx_ledger"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    # CREDIT | DEBIT | REVERSAL | BONUS | ADJUSTMENT | REFUND | SERVER_PURCHASE | UPGRADE | REFERRAL_REWARD
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # signed
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    reference_type: Mapped[str] = mapped_column(String(40), default="")  # conversion|server|upgrade|...
    reference_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(36), default="system")


class CvxRule(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "cvx_rules"

    key: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(20), default="number")  # number|bool|string|json
    label: Mapped[str] = mapped_column(String(160), default="")
    section: Mapped[str] = mapped_column(String(40), default="general", index=True)
    public: Mapped[bool] = mapped_column(Boolean, default=False)


class Campaign(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    kind: Mapped[str] = mapped_column(String(30), default="bonus")  # bonus|multiplier
    applies_to: Mapped[str] = mapped_column(String(40), default="all")  # all|referral|offerwall
    starts_at: Mapped[str] = mapped_column(String(40), default="")
    ends_at: Mapped[str] = mapped_column(String(40), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")
