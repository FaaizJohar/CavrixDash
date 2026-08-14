from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Provider(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "providers"

    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)  # cpa_lead | ad_gem | ...
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), default="offerwall")  # offerwall|ad|link|mock
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="connected")  # connected|disconnected|error
    priority: Mapped[int] = mapped_column(Integer, default=0)
    reward_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    reliability: Mapped[float] = mapped_column(Float, default=1.0)
    revenue_tracked: Mapped[float] = mapped_column(Float, default=0.0)
    meta: Mapped[str] = mapped_column(Text, default="{}")  # JSON provider-specific metadata
    last_synced_at: Mapped[str] = mapped_column(String(40), default="")
    last_attempt_at: Mapped[str] = mapped_column(String(40), default="")
    sync_error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")


class ProviderCredential(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "provider_credentials"

    provider_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)  # api_key | secret_key | ...
    value_encrypted: Mapped[str] = mapped_column(Text, default="")
    masked: Mapped[str] = mapped_column(String(60), default="")
    rotated_at: Mapped[str] = mapped_column(String(40), default="")
