from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.notification import Announcement, Notification
from app.models.server import PterodactylNode, UserServer
from app.models.tracking import TaskClick
from app.services import pterodactyl_service as panel

log = get_logger("worker")


def expire_servers(db: Session) -> None:
    now = datetime.now(timezone.utc)
    cutoff = (now + timedelta(hours=12)).isoformat()
    expiring = (
        db.query(UserServer)
        .filter(UserServer.expires_at != "", UserServer.expires_at != "0", UserServer.expires_at <= cutoff)
        .all()
    )
    for s in expiring:
        try:
            client = panel.get_client(db)
            client.suspend(s.pterodactyl_server_id)
            s.status = "suspended"
        except Exception as exc:
            log.warning("server_suspend_failed", server=s.id, exc=repr(exc))
    if expiring:
        db.commit()
        log.info("servers_suspended", count=len(expiring))


def sync_nodes(db: Session) -> None:
    try:
        client = panel.get_client(db)
        nodes = client.get_nodes()
    except Exception:
        return
    for raw in nodes:
        attrs = raw.get("attributes", {})
        pid = str(attrs.get("id", ""))
        if not pid:
            continue
        row = db.query(PterodactylNode).filter(PterodactylNode.pterodactyl_id == pid).first()
        if not row:
            row = PterodactylNode(pterodactyl_id=pid)
            db.add(row)
        row.name = attrs.get("name", row.name)
        row.fqdn = attrs.get("fqdn", row.fqdn)
        limits = attrs.get("limits", {})
        allocation = attrs.get("allocations", {})
        row.memory_limit = int(limits.get("memory", 0))
        row.disk_limit = int(limits.get("disk", 0))
        row.memory_allocated = int(allocation.get("memory", 0))
        row.disk_allocated = int(allocation.get("disk", 0))
        row.status = attrs.get("status", row.status)
    db.commit()


def expire_tasks(db: Session) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    stale = (
        db.query(TaskClick)
        .filter(TaskClick.status == "pending", TaskClick.created_at < cutoff)
        .all()
    )
    for t in stale:
        t.status = "expired"
    if stale:
        db.commit()
        log.info("tasks_expired", count=len(stale))


def send_announcements(db: Session) -> None:
    now = datetime.now(timezone.utc).isoformat()
    announcements = (
        db.query(Announcement)
        .filter(Announcement.enabled == True)  # noqa: E712
        .all()
    )
    for a in announcements:
        if a.starts_at and a.starts_at > now:
            continue
        if a.ends_at and a.ends_at < now:
            continue
        # Push to matching users once (idempotent by title+created_at)
        key = f"ann:{a.id}"
        from app.core.rate_limit import get, set_ttl

        if get(key):
            continue
        from app.models.user import User

        q = db.query(User).filter(User.status == "active")
        if a.audience == "admins":
            q = q.filter(User.panel_user_id != "")
        users = q.limit(500).all()
        for u in users:
            db.add(
                Notification(
                    user_id=u.id, kind="announcement", title=a.title, body=a.message,
                    link="", priority=a.priority,
                )
            )
        db.commit()
        set_ttl(key, "1", 7 * 24 * 3600)
        log.info("announcement_sent", id=a.id, users=len(users))
