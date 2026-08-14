from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class OverviewStats(BaseModel):
    cvx_balance: float
    cvx_symbol: str
    active_servers: int
    server_limit: int
    tasks_completed: int
    conversions_approved: int
    conversions_pending: int
    daily_limit: float
    earned_today: float
    next_reward_target: float
    next_reward_progress: float
    recent_ledger: list[dict]
    recommended_offers: list[dict]
    servers: list[dict]
    notifications: list[dict]
    server_health: dict


class NotificationOut(ORMModel):
    id: str
    kind: str
    title: str
    body: str
    link: str
    read: bool
    priority: str
    created_at: Any = None


class CreateAnnouncementRequest(BaseModel):
    title: str
    message: str = ""
    audience: str = "all"
    priority: str = "normal"
    starts_at: str = ""
    ends_at: str = ""


class TicketOut(ORMModel):
    id: str
    subject: str
    category: str
    status: str
    priority: str
    created_at: Any = None
    updated_at: Any = None
    last_message: str = ""


class TicketDetail(ORMModel):
    id: str
    subject: str
    category: str
    status: str
    priority: str
    messages: list[dict] = []
    created_at: Any = None


class CreateTicketRequest(BaseModel):
    subject: str
    category: str = "general"
    message: str


class CreateTicketMessageRequest(BaseModel):
    body: str
