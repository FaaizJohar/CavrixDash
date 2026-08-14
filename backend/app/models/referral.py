from __future__ import annotations

from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Referral(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "referrals"

    referrer_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    invitee_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    invitee_email: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending | verified | rewarded | rejected | reversed
    reward_amount: Mapped[float] = mapped_column(Float, default=0.0)
    rewarded_at: Mapped[str] = mapped_column(String(40), default="")
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_ip: Mapped[str] = mapped_column(String(45), default="")
    meta: Mapped[str] = mapped_column(String(1000), default="{}")
