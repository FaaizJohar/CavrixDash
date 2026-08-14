from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, Timestamped


class Kpi(BaseModel):
    key: str
    label: str
    value: Any
    delta: Any = None


class AdminOverview(BaseModel):
    total_revenue: float
    today_revenue: float
    pending_revenue: float
    users: int
    active_users: int
    active_servers: int
    tasks_completed: int
    approved: int
    rejected: int
    reversed: int
    cvx_issued: float
    cvx_spent: float
    cvx_outstanding: float
    provider_revenue: list[dict]
    revenue_7d: list[dict]
    risk_events_24h: int


class AdminUserRow(ORMModel):
    id: str
    email: str
    username: str
    display_name: str
    email_verified: bool
    twofa_enabled: bool
    status: str
    risk_score: float
    cvx_balance: float
    tasks_completed: int
    conversions_approved: int
    active_servers: int = 0
    roles: list[str] = []
    created_at: Any = None


class AdminUserUpdate(BaseModel):
    status: str | None = None
    roles: list[str] | None = None
    cvx_adjustment: float | None = None
    cvx_adjustment_reason: str = ""
    max_servers: int | None = None


class ProviderCreate(BaseModel):
    code: str
    name: str
    kind: str = "offerwall"
    enabled: bool = True
    priority: int = 0
    reward_multiplier: float = 1.0
    credentials: dict[str, str] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    enabled: bool | None = None
    priority: int | None = None
    reward_multiplier: float | None = None
    reliability: float | None = None
    credentials: dict[str, str] | None = None
    meta: dict[str, Any] | None = None


class ProviderOut(Timestamped):
    id: str
    code: str
    name: str
    kind: str
    enabled: bool
    status: str
    priority: int
    reward_multiplier: float
    reliability: float
    revenue_tracked: float
    last_synced_at: str
    last_error: str
    credentials_masked: dict[str, str] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class OfferCreate(BaseModel):
    provider_id: str
    external_id: str = ""
    title: str
    description: str = ""
    category: str = "other"
    reward: float = 0.0
    payout: float = 0.0
    estimated_time: int = 0
    countries: list[str] = Field(default_factory=list)
    devices: list[str] = Field(default_factory=list)
    requirements: str = ""
    conversion_event: str = "action"
    click_url: str = ""
    status: str = "active"
    featured: bool = False
    priority: int = 0
    max_completions: int = 0
    daily_cap: int = 0
    per_user_limit: int = 1
    multiplier: float = 1.0
    starts_at: str = ""
    expires_at: str = ""


class OfferUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    reward: float | None = None
    payout: float | None = None
    estimated_time: int | None = None
    countries: list[str] | None = None
    devices: list[str] | None = None
    requirements: str | None = None
    status: str | None = None
    featured: bool | None = None
    priority: int | None = None
    max_completions: int | None = None
    daily_cap: int | None = None
    per_user_limit: int | None = None
    multiplier: float | None = None
    starts_at: str | None = None
    expires_at: str | None = None


class ConversionAdminUpdate(BaseModel):
    status: str | None = None
    review_note: str = ""


class PlanCreate(BaseModel):
    name: str
    description: str = ""
    cpu: int = 2
    ram_mb: int = 4096
    disk_mb: int = 10240
    backups: int = 1
    databases: int = 0
    allocations: int = 1
    region: str = "default"
    egg_id: str = ""
    nest_id: str = ""
    docker_image: str = ""
    startup: str = ""
    cvx_cost: float = 2500.0
    renewal_cost: float = 0.0
    duration_days: int = 30
    max_servers_per_user: int = 1
    status: str = "active"
    sort_order: int = 0


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cpu: int | None = None
    ram_mb: int | None = None
    disk_mb: int | None = None
    backups: int | None = None
    databases: int | None = None
    allocations: int | None = None
    region: str | None = None
    egg_id: str | None = None
    nest_id: str | None = None
    docker_image: str | None = None
    startup: str | None = None
    cvx_cost: float | None = None
    renewal_cost: float | None = None
    duration_days: int | None = None
    max_servers_per_user: int | None = None
    status: str | None = None
    sort_order: int | None = None


class RegionCreate(BaseModel):
    code: str
    name: str
    flag: str = ""
    enabled: bool = True
    priority: int = 0


class NodeCreate(BaseModel):
    pterodactyl_id: str
    name: str
    region: str = "default"
    fqdn: str = ""
    ip: str = ""
    memory_limit: int = 0
    disk_limit: int = 0
    enabled: bool = True


class TemplateCreate(BaseModel):
    name: str
    software: str
    versions: list[str] = Field(default_factory=list)
    egg_id: str = ""
    nest_id: str = ""
    docker_image: str = ""
    startup: str = ""
    default_plan_id: str = ""
    enabled: bool = True


class CvxSettingsUpdate(BaseModel):
    name: str | None = None
    symbol: str | None = None
    global_multiplier: float | None = None
    min_reward: float | None = None
    max_reward: float | None = None
    daily_limit: float | None = None
    hourly_limit: float | None = None
    max_balance: float | None = None
    referral_reward: float | None = None
    default_task_multiplier: float | None = None


class CampaignCreate(BaseModel):
    name: str
    multiplier: float = 1.0
    kind: str = "bonus"
    applies_to: str = "all"
    starts_at: str = ""
    ends_at: str = ""
    enabled: bool = True
    description: str = ""


class AnnouncementCreate(BaseModel):
    title: str
    message: str = ""
    audience: str = "all"
    priority: str = "normal"
    starts_at: str = ""
    ends_at: str = ""
    enabled: bool = True


class SecretUpdate(BaseModel):
    provider_code: str
    values: dict[str, str] = Field(default_factory=dict)


class PterodactylConfigUpdate(BaseModel):
    panel_url: str | None = None
    api_key: str | None = None
    default_nest: str | None = None
    default_egg: str | None = None
    default_node: str | None = None
    meta: dict[str, Any] | None = None


class SettingsUpdate(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)


class FraudRuleUpdate(BaseModel):
    rules: dict[str, Any] = Field(default_factory=dict)


class AuditRow(ORMModel):
    id: str
    actor_name: str
    action: str
    category: str
    target_type: str
    target_id: str
    old_value: str
    new_value: str
    ip: str
    result: str
    created_at: Any = None


class ConfirmAction(BaseModel):
    confirm_text: str
