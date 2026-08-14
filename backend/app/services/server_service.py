from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.models.cvx import CvxLedger
from app.models.server import (
    PterodactylNode,
    Region,
    ServerPlan,
    ServerTemplate,
    ServerUpgrade,
    UpgradePrice,
    UserServer,
)
from app.models.user import User
from app.services import cvx_service, settings_service as settings_service
from app.services import notification_service
from app.services import pterodactyl_service as panel


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expiry(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def list_plans(db: Session, enabled_only: bool = True) -> list[ServerPlan]:
    q = db.query(ServerPlan).order_by(ServerPlan.sort_order.asc(), ServerPlan.cvx_cost.asc())
    if enabled_only:
        q = q.filter(ServerPlan.status == "active")
    return q.all()


def get_plan(db: Session, plan_id: str) -> ServerPlan:
    plan = db.query(ServerPlan).filter(ServerPlan.id == plan_id).first()
    if not plan:
        raise NotFoundError("Plan not found.")
    return plan


def list_regions(db: Session) -> list[Region]:
    return db.query(Region).order_by(Region.priority.asc()).all()


def list_templates(db: Session, enabled_only: bool = True) -> list[ServerTemplate]:
    q = db.query(ServerTemplate).order_by(ServerTemplate.software.asc())
    if enabled_only:
        q = q.filter(ServerTemplate.enabled == True)  # noqa: E712
    return q.all()


def get_template(db: Session, template_id: str) -> ServerTemplate:
    t = db.query(ServerTemplate).filter(ServerTemplate.id == template_id).first()
    if not t:
        raise NotFoundError("Template not found.")
    return t


def list_upgrade_prices(db: Session) -> list[UpgradePrice]:
    return db.query(UpgradePrice).filter(UpgradePrice.enabled == True).all()  # noqa: E712


def my_servers(db: Session, user_id: str) -> list[UserServer]:
    return (
        db.query(UserServer)
        .filter(UserServer.user_id == user_id)
        .order_by(UserServer.created_at.desc())
        .all()
    )


def get_server(db: Session, user: User, server_id: str) -> UserServer:
    server = db.query(UserServer).filter(UserServer.id == server_id).first()
    if not server:
        raise NotFoundError("Server not found.")
    if server.user_id != user.id and not user.is_admin:
        raise NotFoundError("Server not found.")
    return server


def _server_out(server: UserServer, plan: ServerPlan | None, live: dict | None = None) -> dict[str, Any]:
    return {
        "id": server.id,
        "plan_id": server.plan_id,
        "plan_name": plan.name if plan else "",
        "pterodactyl_server_id": server.pterodactyl_server_id,
        "name": server.name,
        "region": server.region,
        "status": server.status,
        "ip": server.ip,
        "port": server.port,
        "cpu": server.cpu,
        "ram_mb": server.ram_mb,
        "disk_mb": server.disk_mb,
        "backups": server.backups,
        "databases": server.databases,
        "allocations": server.allocations,
        "software": server.software,
        "version": server.version,
        "expires_at": server.expires_at,
        "node": server.node_id,
        "live": live,
        "created_at": server.created_at,
        "updated_at": server.updated_at,
    }


def serialize(db: Session, servers: list[UserServer] | UserServer, with_live: bool = True) -> Any:
    if isinstance(servers, list):
        plans = {p.id: p for p in list_plans(db, enabled_only=False)}
        out = []
        for s in servers:
            live = None
            if with_live and s.status in ("running", "offline"):
                try:
                    live = fetch_resources(db, s)
                except Exception:
                    live = None
            out.append(_server_out(s, plans.get(s.plan_id), live))
        return out
    s = servers
    plan = db.query(ServerPlan).filter(ServerPlan.id == s.plan_id).first()
    live = None
    if with_live and s.status in ("running", "offline"):
        try:
            live = fetch_resources(db, s)
        except Exception:
            live = None
    return _server_out(s, plan, live)


def claim_server(
    db: Session,
    user: User,
    *,
    plan_id: str,
    region: str,
    template_id: str | None,
    version: str,
    server_name: str,
    ip: str,
) -> UserServer:
    if not settings_service.get_value(db, "minecraft.server_claims_enabled", True):
        raise AppError("Server claims are temporarily disabled.", code="CLAIMS_DISABLED")

    plan = get_plan(db, plan_id)
    if plan.status != "active":
        raise AppError("This plan is not available.", code="PLAN_UNAVAILABLE")

    max_servers = int(settings_service.get_value(db, "minecraft.max_servers_per_user", settings.servers_max_per_user))
    count = db.query(UserServer).filter(UserServer.user_id == user.id).count()
    if count >= max_servers:
        raise AppError(f"You already have {max_servers} servers. Upgrade one or delete one.", code="SERVER_LIMIT")

    template = None
    if template_id:
        template = get_template(db, template_id)

    # region validation
    region_obj = db.query(Region).filter(Region.code == region, Region.enabled == True).first()  # noqa: E712
    if not region_obj:
        region = "default"
        region_obj = db.query(Region).filter(Region.code == "default", Region.enabled == True).first()  # noqa: E712
    if not region_obj:
        raise AppError("No server region is available.", code="NO_REGION")

    # pay
    cvx_service.debit(
        db, user, plan.cvx_cost, "SERVER_PURCHASE",
        f"Server '{server_name}' ({plan.name})",
        reference_type="server_plan", reference_id=plan.id,
        created_by="user",
    )

    # provision via panel
    try:
        panel_user_id = panel.ensure_panel_user(db, user)
        node = _pick_node(db, region)
        egg_id = int(template.egg_id or plan.egg_id) if (template.egg_id or plan.egg_id) else None
        nest_id = int(template.nest_id or plan.nest_id) if (template.nest_id or plan.nest_id) else None
        if egg_id is None or nest_id is None:
            raise AppError("Server template is not fully configured.", code="TEMPLATE_INCOMPLETE")

        attrs = panel.get_client(db).create_server(
            name=server_name,
            user_id=panel_user_id,
            egg_id=egg_id,
            nest_id=nest_id,
            docker_image=template.docker_image or plan.docker_image,
            startup=template.startup or plan.startup,
            environment={"SERVER_NAME": server_name, "VERSION": version},
            cpu=plan.cpu,
            ram_mb=plan.ram_mb,
            disk_mb=plan.disk_mb,
            databases=plan.databases,
            backups=plan.backups,
            node_id=int(node.pterodactyl_id) if node else None,
        )
        pterodactyl_id = str(attrs.get("id") or attrs.get("uuid") or "")
    except AppError:
        cvx_service.refund(db, user, plan.cvx_cost, "Server provisioning failed; CVX refunded.", reference_type="server_plan")
        raise

    server = UserServer(
        user_id=user.id,
        plan_id=plan.id,
        pterodactyl_server_id=pterodactyl_id,
        name=server_name,
        egg_id=template.egg_id if template else plan.egg_id,
        nest_id=template.nest_id if template else plan.nest_id,
        region=region,
        node_id=node.id if node else "",
        status="provisioning",
        cpu=plan.cpu,
        ram_mb=plan.ram_mb,
        disk_mb=plan.disk_mb,
        backups=plan.backups,
        databases=plan.databases,
        allocations=plan.allocations,
        software=(template.software if template else "vanilla"),
        version=version,
        expires_at=_expiry(int(settings_service.get_value(db, "minecraft.default_duration_days", plan.duration_days))),
        last_activity_at=_now(),
        meta=json.dumps({"identifier": pterodactyl_id}),
    )
    db.add(server)
    db.commit()
    db.refresh(server)

    notification_service.push(
        db, user.id, "server_provisioning",
        "Server provisioning",
        f"'{server_name}' is being provisioned. It will be ready in a few minutes.",
        link=f"/minecraft/{server.id}",
    )
    return server


def _pick_node(db: Session, region: str) -> PterodactylNode | None:
    node = (
        db.query(PterodactylNode)
        .filter(PterodactylNode.region == region, PterodactylNode.enabled == True)  # noqa: E712
        .order_by(PterodactylNode.memory_allocated.asc())
        .first()
    )
    if not node:
        node = (
            db.query(PterodactylNode)
            .filter(PterodactylNode.enabled == True)  # noqa: E712
            .order_by(PterodactylNode.memory_allocated.asc())
            .first()
        )
    return node


def fetch_resources(db: Session, server: UserServer) -> dict[str, Any]:
    client = panel.get_client(db)
    identifier = panel.server_identifier(server)
    r = client.server_resources(identifier)
    return {
        "state": r.get("current_state", server.status),
        "cpu_absolute": r.get("cpu_absolute", 0),
        "memory_bytes": r.get("memory_bytes", 0),
        "disk_bytes": r.get("disk_bytes", 0),
        "uptime": r.get("uptime", 0),
        "memory_limit_bytes": server.ram_mb * 1024 * 1024,
        "disk_limit_bytes": server.disk_mb * 1024 * 1024,
    }


def server_action(db: Session, user: User, server: UserServer, action: str) -> dict[str, Any]:
    client = panel.get_client(db)
    identifier = panel.server_identifier(server)
    if action in ("start", "stop", "restart", "kill"):
        client.power(identifier, action)
        server.status = "running" if action == "start" else server.status
    elif action == "reinstall":
        client.reinstall(server.pterodactyl_server_id)
        server.status = "provisioning"
    else:
        raise AppError("Invalid action.", code="INVALID_ACTION")
    server.last_activity_at = _now()
    db.commit()
    return {"ok": True, "status": server.status}


def console_ws_url(db: Session, user: User, server: UserServer) -> dict[str, Any]:
    client = panel.get_client(db)
    identifier = panel.server_identifier(server)
    return client.websocket(identifier)


def list_files(db: Session, server: UserServer, path: str = "/") -> list[dict[str, Any]]:
    client = panel.get_client(db)
    return client.list_files(panel.server_identifier(server), path)


def list_backups(db: Session, server: UserServer) -> list[dict[str, Any]]:
    client = panel.get_client(db)
    return client.list_backups(panel.server_identifier(server))


def restore_backup(db: Session, server: UserServer, backup_id: str) -> None:
    client = panel.get_client(db)
    client.restore_backup(panel.server_identifier(server), backup_id)


def list_schedules(db: Session, server: UserServer) -> list[dict[str, Any]]:
    client = panel.get_client(db)
    return client.list_schedules(panel.server_identifier(server))


def list_network(db: Session, server: UserServer) -> list[dict[str, Any]]:
    client = panel.get_client(db)
    return client.list_allocations(panel.server_identifier(server))


def quote_upgrade(db: Session, server: UserServer, upgrade_type: str, amount: float) -> dict[str, Any]:
    price = db.query(UpgradePrice).filter(UpgradePrice.upgrade_type == upgrade_type, UpgradePrice.enabled == True).first()  # noqa: E712
    if not price:
        raise NotFoundError("This upgrade is not available.")
    units = max(1, int(amount / price.unit_size)) if price.unit_size else 1
    cost = round(price.cvx_cost * units, 2)
    current, new = _resource_for(server, upgrade_type)
    new = new + price.unit_size * units
    return {
        "server_id": server.id,
        "upgrade_type": upgrade_type,
        "amount": units,
        "cvx_cost": cost,
        "label": price.label,
        "unit": price.unit,
        "new_value": new,
        "current_value": current,
    }


def buy_upgrade(db: Session, user: User, server: UserServer, upgrade_type: str, amount: float) -> ServerUpgrade:
    quote = quote_upgrade(db, server, upgrade_type, amount)
    cvx_service.debit(
        db, user, quote["cvx_cost"], "UPGRADE",
        f"{quote['label']} on '{server.name}'",
        reference_type="server", reference_id=server.id,
        created_by="user",
    )
    up = ServerUpgrade(
        user_id=user.id,
        server_id=server.id,
        upgrade_type=upgrade_type,
        label=quote["label"],
        amount=quote["amount"],
        unit=quote["unit"],
        cvx_cost=quote["cvx_cost"],
        status="applied",
    )
    db.add(up)
    db.flush()

    # apply resource bump (panel limits)
    current, _ = _resource_for(server, upgrade_type)
    new = quote["new_value"]
    client = panel.get_client(db)
    identifier = panel.server_identifier(server)
    limits = {"memory": server.ram_mb, "disk": server.disk_mb, "cpu": server.cpu}
    if upgrade_type == "ram":
        server.ram_mb = int(new)
        limits["memory"] = server.ram_mb
    elif upgrade_type == "disk":
        server.disk_mb = int(new)
        limits["disk"] = server.disk_mb
    elif upgrade_type == "cpu":
        server.cpu = int(new)
        limits["cpu"] = server.cpu
    elif upgrade_type == "backup":
        server.backups += int(quote["amount"])
    elif upgrade_type == "database":
        server.databases += int(quote["amount"])
    elif upgrade_type == "allocation":
        server.allocations += int(quote["amount"])
    db.commit()
    db.refresh(up)
    notification_service.push(
        db, user.id, "server_upgrade",
        "Server upgraded",
        f"{quote['label']} applied to '{server.name}'.",
        link=f"/minecraft/{server.id}",
    )
    return up


def _resource_for(server: UserServer, upgrade_type: str) -> tuple[float, float]:
    mapping = {
        "ram": (server.ram_mb, server.ram_mb),
        "disk": (server.disk_mb, server.disk_mb),
        "cpu": (server.cpu, server.cpu),
        "backup": (server.backups, server.backups),
        "database": (server.databases, server.databases),
        "allocation": (server.allocations, server.allocations),
    }
    return mapping.get(upgrade_type, (0, 0))


def renew_server(db: Session, user: User, server: UserServer) -> UserServer:
    plan = get_plan(db, server.plan_id)
    if plan.renewal_cost > 0:
        cvx_service.debit(db, user, plan.renewal_cost, "SERVER_PURCHASE", f"Renew '{server.name}'", reference_type="server", reference_id=server.id)
    old = server.expires_at
    try:
        old_dt = datetime.fromisoformat(old) if old else datetime.now(timezone.utc)
    except Exception:
        old_dt = datetime.now(timezone.utc)
    server.expires_at = (old_dt + timedelta(days=plan.duration_days)).isoformat()
    server.last_renewed_at = _now()
    db.commit()
    db.refresh(server)
    return server


def destroy_server(db: Session, server: UserServer, *, confirm_token: str = "") -> None:
    client = panel.get_client(db)
    client.delete(server.pterodactyl_server_id)
    db.delete(server)
    db.commit()
