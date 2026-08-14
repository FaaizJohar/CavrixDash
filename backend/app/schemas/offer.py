from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, Timestamped


class OfferOut(Timestamped):
    id: str
    provider_code: str
    provider_name: str
    provider_kind: str
    title: str
    description: str
    category: str
    icon_url: str
    reward: float
    estimated_time: int
    countries: list[str]
    devices: list[str]
    requirements: str
    conversion_event: str
    featured: bool
    priority: int
    status: str
    conversion_rate: float
    approval_rate: float
    completion_count: int
    effective_reward: float
    click_url: str = ""
    starts_at: str = ""
    expires_at: str = ""


class OfferDetail(OfferOut):
    landing_url: str = ""


class OfferFeedQuery(BaseModel):
    category: str | None = None
    sort: str = "recommended"  # reward|recommended|new|fastest|conversion|reliable
    device: str | None = None
    country: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=24, ge=1, le=100)


class ClickResponse(BaseModel):
    click_id: str
    redirect_url: str
    expires_in: int = 120


class ClickRequest(BaseModel):
    offer_id: str


class TaskOut(ORMModel):
    id: str
    click_id: str
    offer_id: str
    offer_title: str
    provider_code: str
    category: str
    reward_offered: float
    status: str
    risk_score: float
    external_tx_id: str = ""
    created_at: Any = None
    updated_at: Any = None
