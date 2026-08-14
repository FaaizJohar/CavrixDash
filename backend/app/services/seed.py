from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.cvx import CvxRule
from app.models.notification import Announcement
from app.models.server import PterodactylNode, Region, ServerPlan, ServerTemplate, UpgradePrice
from app.models.user import Permission, Role, User


def _roles(db: Session) -> None:
    existing = {r.name for r in db.query(Role).all()}
    names = [
        ("super_admin", True),
        ("admin", True),
        ("support", True),
        ("moderator", True),
        ("user", True),
        ("finance_admin", True),
        ("infra_admin", True),
    ]
    for name, is_system in names:
        if name not in existing:
            db.add(Role(name=name, description=f"{name} role", is_system=is_system))
    db.commit()


def _admin(db: Session) -> None:
    if db.query(User).filter(User.email == settings.seed_admin_email).first():
        return
    super_role = db.query(Role).filter(Role.name == "super_admin").first()
    user_role = db.query(Role).filter(Role.name == "user").first()
    from app.services.user_service import _referral_code

    admin = User(
        email=settings.seed_admin_email,
        username="admin",
        display_name="Cavrix Admin",
        password_hash=hash_password(settings.seed_admin_password),
        referral_code=_referral_code(),
        email_verified=True,
        status="active",
    )
    if super_role:
        admin.roles.append(super_role)
    if user_role:
        admin.roles.append(user_role)
    db.add(admin)
    db.commit()


def _regions(db: Session) -> None:
    if db.query(Region).count() > 0:
        return
    for i, (code, name, flag) in enumerate(
        [
            ("default", "Global", "🌍"),
            ("in", "Mumbai", "🇮🇳"),
            ("us", "New York", "🇺🇸"),
            ("eu", "Frankfurt", "🇪🇺"),
            ("sg", "Singapore", "🇸🇬"),
        ]
    ):
        db.add(Region(code=code, name=name, flag=flag, enabled=True, priority=i))
    db.commit()


def _plans(db: Session) -> None:
    if db.query(ServerPlan).count() > 0:
        return
    db.add_all(
        [
            ServerPlan(
                name="Starter", description="Perfect for getting started", cpu=2, ram_mb=4096,
                disk_mb=10240, backups=1, region="default", cvx_cost=2500, renewal_cost=1500,
                duration_days=30, status="active", sort_order=0,
            ),
            ServerPlan(
                name="Gamer", description="4GB RAM for friends and plugins", cpu=3, ram_mb=6144,
                disk_mb=15360, backups=2, databases=1, region="default", cvx_cost=4500, renewal_cost=3000,
                duration_days=30, status="active", sort_order=1,
            ),
            ServerPlan(
                name="Pro", description="Full power for big communities", cpu=4, ram_mb=8192,
                disk_mb=20480, backups=3, databases=1, region="default", cvx_cost=7500, renewal_cost=5000,
                duration_days=30, status="active", sort_order=2,
            ),
        ]
    )
    db.commit()


def _templates(db: Session) -> None:
    if db.query(ServerTemplate).count() > 0:
        return
    db.add_all(
        [
            ServerTemplate(
                name="Vanilla", software="vanilla", versions=json.dumps(["1.21.4", "1.21.1", "1.20.6"]),
                egg_id="1", nest_id="1", docker_image="ghcr.io/pterodactyl/yolks:java_21",
                startup="java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar",
                default_plan_id="", enabled=True,
            ),
            ServerTemplate(
                name="Paper", software="paper", versions=json.dumps(["1.21.4", "1.21.1", "1.20.6"]),
                egg_id="2", nest_id="1", docker_image="ghcr.io/pterodactyl/yolks:java_21",
                startup="java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar",
                default_plan_id="", enabled=True,
            ),
            ServerTemplate(
                name="Forge", software="forge", versions=json.dumps(["1.20.1", "1.19.4"]),
                egg_id="3", nest_id="1", docker_image="ghcr.io/pterodactyl/yolks:java_17",
                startup="java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar forge-installer.jar --installServer",
                default_plan_id="", enabled=True,
            ),
            ServerTemplate(
                name="Fabric", software="fabric", versions=json.dumps(["1.21.4", "1.20.6"]),
                egg_id="4", nest_id="1", docker_image="ghcr.io/pterodactyl/yolks:java_21",
                startup="java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar fabric-server-launch.jar",
                default_plan_id="", enabled=True,
            ),
        ]
    )
    db.commit()


def _upgrade_prices(db: Session) -> None:
    if db.query(UpgradePrice).count() > 0:
        return
    db.add_all(
        [
            UpgradePrice(upgrade_type="ram", label="RAM", unit="MB", unit_size=1024, cvx_cost=800, enabled=True),
            UpgradePrice(upgrade_type="cpu", label="CPU", unit="core", unit_size=1, cvx_cost=1000, enabled=True),
            UpgradePrice(upgrade_type="disk", label="Disk", unit="GB", unit_size=1024, cvx_cost=400, enabled=True),
            UpgradePrice(upgrade_type="backup", label="Backup slot", unit="slot", unit_size=1, cvx_cost=500, enabled=True),
            UpgradePrice(upgrade_type="database", label="Database", unit="db", unit_size=1, cvx_cost=300, enabled=True),
            UpgradePrice(upgrade_type="allocation", label="Allocation", unit="alloc", unit_size=1, cvx_cost=200, enabled=True),
        ]
    )
    db.commit()


def _cvx_rules(db: Session) -> None:
    if db.query(CvxRule).count() > 0:
        return
    defaults = [
        ("cvx.name", "CVX", "string", "Currency name", "cvx"),
        ("cvx.symbol", "CVX", "string", "Currency symbol", "cvx"),
        ("cvx.daily_limit", "5000", "number", "Daily earning limit", "cvx"),
        ("cvx.hourly_limit", "1000", "number", "Hourly earning limit", "cvx"),
        ("cvx.max_balance", "100000", "number", "Max CVX balance", "cvx"),
        ("cvx.global_multiplier", "1.0", "number", "Global reward multiplier", "cvx"),
        ("cvx.min_reward", "50", "number", "Minimum reward", "cvx"),
        ("cvx.max_reward", "100000", "number", "Maximum reward", "cvx"),
        ("tasks.offers_enabled", "true", "bool", "Offer wall enabled", "task"),
        ("tasks.tasks_enabled", "true", "bool", "Tasks enabled", "task"),
        ("tasks.max_daily_tasks", "100", "number", "Max daily tasks", "task"),
        ("minecraft.server_claims_enabled", "true", "bool", "Server claims enabled", "server"),
        ("minecraft.min_cvx", "2500", "number", "Minimum CVX to claim a server", "server"),
        ("minecraft.max_servers_per_user", "3", "number", "Max servers per user", "server"),
        ("minecraft.default_duration_days", "30", "number", "Default server duration (days)", "server"),
        ("referral.enabled", "true", "bool", "Referrals enabled", "referral"),
        ("referral.reward", "250", "number", "Referral reward (CVX)", "referral"),
        ("referral.max_monthly", "10", "number", "Max rewarded referrals per month", "referral"),
    ]
    for key, value, kind, label, section in defaults:
        db.add(CvxRule(key=key, value=value, kind=kind, label=label, section=section, public=True))
    db.commit()


def _providers(db: Session) -> None:
    from app.models.provider import Provider
    from app.providers.registry import list_adapters

    existing = {p.code for p in db.query(Provider).all()}
    for adapter in list_adapters():
        if adapter["code"] in existing:
            continue
        if adapter["code"] == "mock" and not settings.mock_provider_enabled:
            continue
        db.add(
            Provider(
                code=adapter["code"], name=adapter["name"], kind=adapter["kind"],
                enabled=True, status="connected", priority=0,
            )
        )
    db.commit()


def _mock_offers(db: Session) -> None:
    from app.models.offer import Offer
    from app.models.provider import Provider

    if not settings.mock_provider_enabled:
        return
    if db.query(Offer).count() > 0:
        return
    from app.providers.registry import get_adapter

    mock = db.query(Provider).filter(Provider.code == "mock").first()
    if not mock:
        return
    adapter = get_adapter("mock")
    now = datetime.now(timezone.utc)
    for i, raw in enumerate(adapter.sync_offers({})):
        db.add(
            Offer(
                provider_id=mock.id,
                external_id=raw["external_id"],
                title=raw["title"],
                description=raw.get("description", ""),
                category=raw.get("category", "other"),
                icon_url=raw.get("icon_url", ""),
                reward=raw.get("reward", 0),
                payout=raw.get("payout", 0),
                estimated_time=raw.get("estimated_time", 0),
                countries=json.dumps(raw.get("countries", [])),
                devices=json.dumps(raw.get("devices", [])),
                requirements=raw.get("requirements", ""),
                conversion_event=raw.get("conversion_event", "action"),
                click_url=raw.get("click_url", ""),
                landing_url=raw.get("landing_url", ""),
                tracking_url=raw.get("tracking_url", ""),
                status="active",
                featured=i == 0,
                priority=5 - i,
                conversion_rate=0.08,
                approval_rate=0.92,
                created_by="seed",
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()


def _welcome(db: Session) -> None:
    if db.query(Announcement).count() > 0:
        return
    db.add(
        Announcement(
            title="Welcome to Cavrix Cloud",
            message="Earn CVX credits by completing offers, then redeem them for Minecraft servers and upgrades.",
            audience="all", priority="normal", enabled=True,
        )
    )
    db.commit()


def ensure_bootstrap(db: Session | None = None) -> None:
    """Create roles, admin, plans, regions, templates, providers, rules."""
    own = db is None
    db = db or SessionLocal()
    try:
        _roles(db)
        _admin(db)
        _regions(db)
        _plans(db)
        _templates(db)
        _upgrade_prices(db)
        _cvx_rules(db)
        _providers(db)
        _mock_offers(db)
        _welcome(db)
    finally:
        if own:
            db.close()
