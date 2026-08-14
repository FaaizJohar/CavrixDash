from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel, Timestamped


class PlanOut(Timestamped):
    id: str
    name: str
    description: str
    cpu: int
    ram_mb: int
    disk_mb: int
    backups: int
    databases: int
    allocations: int
    region: str
    egg_id: str
    nest_id: str
    docker_image: str
    startup: str
    cvx_cost: float
    renewal_cost: float
    duration_days: int
    max_servers_per_user: int
    status: str
    sort_order: int


class ServerOut(Timestamped):
    id: str
    plan_id: str
    plan_name: str = ""
    pterodactyl_server_id: str
    name: str
    region: str
    status: str
    ip: str
    port: int
    cpu: int
    ram_mb: int
    disk_mb: int
    backups: int
    databases: int
    allocations: int
    software: str
    version: str
    expires_at: str
    node: Any = None
    live: Any = None


class CreateServerRequest(BaseModel):
    plan_id: str
    region: str = "default"
    template_id: str | None = None
    version: str = "latest"
    server_name: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9_-]+$")


class ServerActionRequest(BaseModel):
    action: str  # start|stop|restart|kill|reinstall


class UpgradeQuote(BaseModel):
    server_id: str
    upgrade_type: str  # ram|cpu|disk|backup|database|allocation
    amount: float = 1.0
    cvx_cost: float
    label: str
    unit: str
    new_value: float
    current_value: float


class UpgradePurchaseRequest(BaseModel):
    server_id: str
    upgrade_type: str
    amount: float = Field(default=1.0, ge=0.1)


class UpgradeOut(ORMModel):
    id: str
    server_id: str
    upgrade_type: str
    label: str
    amount: float
    unit: str
    cvx_cost: float
    status: str
    created_at: Any = None


class UpgradePriceOut(ORMModel):
    upgrade_type: str
    label: str
    unit: str
    unit_size: float
    cvx_cost: float
    enabled: bool


class RegionOut(ORMModel):
    code: str
    name: str
    flag: str
    enabled: bool
    priority: int


class NodeOut(ORMModel):
    id: str
    name: str
    region: str
    fqdn: str
    memory_allocated: int
    memory_limit: int
    disk_allocated: int
    disk_limit: int
    enabled: bool
    status: str


class TemplateOut(ORMModel):
    id: str
    name: str
    software: str
    versions: list[str]
    egg_id: str
    nest_id: str
    docker_image: str
    startup: str
    default_plan_id: str
    enabled: bool

    @field_validator("versions", mode="before")
    @classmethod
    def _parse_versions(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v
