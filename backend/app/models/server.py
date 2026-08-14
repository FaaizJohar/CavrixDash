from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ServerPlan(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "server_plans"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    cpu: Mapped[int] = mapped_column(Integer, default=2)
    ram_mb: Mapped[int] = mapped_column(Integer, default=4096)
    disk_mb: Mapped[int] = mapped_column(Integer, default=10240)
    backups: Mapped[int] = mapped_column(Integer, default=1)
    databases: Mapped[int] = mapped_column(Integer, default=0)
    allocations: Mapped[int] = mapped_column(Integer, default=1)
    region: Mapped[str] = mapped_column(String(40), default="default")
    egg_id: Mapped[str] = mapped_column(String(36), default="")
    nest_id: Mapped[str] = mapped_column(String(36), default="")
    docker_image: Mapped[str] = mapped_column(String(200), default="")
    startup: Mapped[str] = mapped_column(Text, default="")
    cvx_cost: Mapped[float] = mapped_column(Float, default=0.0)
    renewal_cost: Mapped[float] = mapped_column(Float, default=0.0)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    max_servers_per_user: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[str] = mapped_column(Text, default="{}")


class UserServer(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "servers"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    plan_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    pterodactyl_server_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    egg_id: Mapped[str] = mapped_column(String(36), default="")
    nest_id: Mapped[str] = mapped_column(String(36), default="")
    region: Mapped[str] = mapped_column(String(40), default="default")
    node_id: Mapped[str] = mapped_column(String(36), default="")
    status: Mapped[str] = mapped_column(String(20), default="provisioning", index=True)
    # provisioning | running | offline | suspended | error | deleted
    ip: Mapped[str] = mapped_column(String(45), default="")
    port: Mapped[int] = mapped_column(Integer, default=0)
    cpu: Mapped[int] = mapped_column(Integer, default=2)
    ram_mb: Mapped[int] = mapped_column(Integer, default=4096)
    disk_mb: Mapped[int] = mapped_column(Integer, default=10240)
    backups: Mapped[int] = mapped_column(Integer, default=1)
    databases: Mapped[int] = mapped_column(Integer, default=0)
    allocations: Mapped[int] = mapped_column(Integer, default=1)
    software: Mapped[str] = mapped_column(String(60), default="vanilla")
    version: Mapped[str] = mapped_column(String(30), default="")
    expires_at: Mapped[str] = mapped_column(String(40), default="")
    last_renewed_at: Mapped[str] = mapped_column(String(40), default="")
    last_activity_at: Mapped[str] = mapped_column(String(40), default="")
    provisioning_error: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")


class ServerUpgrade(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "server_upgrades"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    server_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    upgrade_type: Mapped[str] = mapped_column(String(30), nullable=False)  # ram|cpu|disk|backup|database|allocation
    label: Mapped[str] = mapped_column(String(120), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(10), default="")
    cvx_cost: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="applied", index=True)
    pterodactyl_job: Mapped[str] = mapped_column(String(120), default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")


class PterodactylNode(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "pterodactyl_nodes"

    pterodactyl_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(40), default="default", index=True)
    fqdn: Mapped[str] = mapped_column(String(200), default="")
    ip: Mapped[str] = mapped_column(String(45), default="")
    memory_allocated: Mapped[int] = mapped_column(Integer, default=0)
    memory_limit: Mapped[int] = mapped_column(Integer, default=0)
    disk_allocated: Mapped[int] = mapped_column(Integer, default=0)
    disk_limit: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="online")
    meta: Mapped[str] = mapped_column(Text, default="{}")


class Region(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    flag: Mapped[str] = mapped_column(String(4), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[str] = mapped_column(Text, default="{}")


class ServerTemplate(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "server_templates"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    software: Mapped[str] = mapped_column(String(60), nullable=False, index=True)  # vanilla|paper|spigot|forge|fabric|bedrock
    versions: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    egg_id: Mapped[str] = mapped_column(String(36), default="")
    nest_id: Mapped[str] = mapped_column(String(36), default="")
    docker_image: Mapped[str] = mapped_column(String(200), default="")
    startup: Mapped[str] = mapped_column(Text, default="")
    default_plan_id: Mapped[str] = mapped_column(String(36), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[str] = mapped_column(Text, default="{}")


class UpgradePrice(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "upgrade_prices"

    upgrade_type: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)  # ram|cpu|disk|backup|database|allocation
    label: Mapped[str] = mapped_column(String(120), default="")
    unit: Mapped[str] = mapped_column(String(10), default="")
    unit_size: Mapped[float] = mapped_column(Float, default=1.0)
    cvx_cost: Mapped[float] = mapped_column(Float, default=0.0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
