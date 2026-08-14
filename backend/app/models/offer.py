from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Offer(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "offers"

    provider_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="other", index=True)  # apps|games|software|surveys|trials|cpa|cpi|cpe|lead|other
    icon_url: Mapped[str] = mapped_column(String(512), default="")
    reward: Mapped[float] = mapped_column(Float, default=0.0)
    payout: Mapped[float] = mapped_column(Float, default=0.0)  # revenue to us per conversion
    estimated_time: Mapped[int] = mapped_column(Integer, default=0)  # minutes
    countries: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    devices: Mapped[str] = mapped_column(Text, default="[]")  # JSON list [android, ios, web]
    requirements: Mapped[str] = mapped_column(Text, default="")  # HTML / markdown
    conversion_event: Mapped[str] = mapped_column(String(80), default="action")
    click_url: Mapped[str] = mapped_column(Text, default="")
    landing_url: Mapped[str] = mapped_column(Text, default="")
    tracking_url: Mapped[str] = mapped_column(Text, default="")  # postback URL template

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|paused|hidden|expired
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    max_completions: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited
    daily_cap: Mapped[int] = mapped_column(Integer, default=0)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1)
    min_user_level: Mapped[int] = mapped_column(Integer, default=0)

    conversion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    approval_rate: Mapped[float] = mapped_column(Float, default=0.0)
    completion_count: Mapped[int] = mapped_column(Integer, default=0)
    revenue_earned: Mapped[float] = mapped_column(Float, default=0.0)

    starts_at: Mapped[str] = mapped_column(String(40), default="")
    expires_at: Mapped[str] = mapped_column(String(40), default="")
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    meta: Mapped[str] = mapped_column(Text, default="{}")

    created_by: Mapped[str] = mapped_column(String(36), default="")

    @property
    def effective_reward(self) -> float:
        return round(self.reward * self.multiplier, 2)
