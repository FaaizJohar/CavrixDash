from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cvx import CvxLedger
from app.models.notification import Announcement, Notification
from app.models.provider import Provider
from app.models.server import ServerPlan, UserServer
from app.models.tracking import Conversion, TaskClick
from app.models.user import User
from app.services import cvx_service, settings_service as settings
from app.services import server_service


def _datalist(row) -> list[dict[str, Any]]:
    try:
        return json.loads(row.meta or "[]")
    except Exception:
        return []


def overview(db: Session, user: User) -> dict[str, Any]:
    wallet = cvx_service.get_wallet(db, user)
    servers = server_service.my_servers(db, user.id)
    server_limit = int(settings.get_value(db, "minecraft.max_servers_per_user", 3))

    recent = (
        db.query(CvxLedger)
        .filter(CvxLedger.user_id == user.id)
        .order_by(CvxLedger.created_at.desc())
        .limit(6)
        .all()
    )
    recent_ledger = [
        {
            "id": l.id,
            "transaction_type": l.transaction_type,
            "amount": l.amount,
            "balance_after": l.balance_after,
            "description": l.description,
            "created_at": l.created_at,
        }
        for l in recent
    ]

    # recommended offers (top 4 featured/priority)
    from app.services import task_service

    offers, _ = task_service.list_offers(db, sort="recommended", page=1, page_size=4)
    providers = {p.id: p for p in db.query(Provider).all()}
    recommended = [
        {
            "id": o.id,
            "title": o.title,
            "category": o.category,
            "reward": o.effective_reward,
            "estimated_time": o.estimated_time,
            "icon_url": o.icon_url,
            "provider_name": providers.get(o.provider_id).name if providers.get(o.provider_id) else "",
            "featured": o.featured,
        }
        for o in offers
    ]

    # notifications unread
    notif_rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read == False)  # noqa: E712
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )
    notifications = [
        {
            "id": n.id,
            "kind": n.kind,
            "title": n.title,
            "body": n.body,
            "link": n.link,
            "priority": n.priority,
            "created_at": n.created_at,
        }
        for n in notif_rows
    ]

    server_health = {
        "running": sum(1 for s in servers if s.status == "running"),
        "provisioning": sum(1 for s in servers if s.status == "provisioning"),
        "offline": sum(1 for s in servers if s.status == "offline"),
        "total": len(servers),
    }

    next_reward_target = float(settings.get_value(db, "minecraft.min_cvx", 2500))
    balance = float(user.cvx_balance or 0)
    progress = min(100.0, round(balance / next_reward_target * 100, 1)) if next_reward_target else 0.0

    return {
        "cvx_balance": wallet["balance"],
        "cvx_symbol": str(settings.get_value(db, "cvx.symbol", "CVX")),
        "active_servers": len(servers),
        "server_limit": server_limit,
        "tasks_completed": user.tasks_completed or 0,
        "conversions_approved": user.conversions_approved or 0,
        "conversions_pending": user.conversions_pending or 0,
        "daily_limit": wallet["daily_limit"],
        "earned_today": wallet["earned_today"],
        "next_reward_target": next_reward_target,
        "next_reward_progress": progress,
        "recent_ledger": recent_ledger,
        "recommended_offers": recommended,
        "servers": [server_service.serialize(db, s, with_live=False) for s in servers[:3]],
        "notifications": notifications,
        "server_health": server_health,
    }


def user_time_series(db: Session, user: User, days: int = 30) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(func.date_trunc("day", CvxLedger.created_at).label("day"), func.sum(CvxLedger.amount).label("net"))
        .filter(CvxLedger.user_id == user.id, CvxLedger.created_at >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [
        {
            "day": r.day.isoformat()[:10] if hasattr(r.day, "isoformat") else str(r.day)[:10],
            "net": round(float(r.net or 0), 2),
        }
        for r in rows
    ]


def conversions_breakdown(db: Session, user: User, page: int = 1, page_size: int = 20) -> tuple[list[Conversion], int]:
    q = (
        db.query(Conversion)
        .filter(Conversion.user_id == user.id)
        .order_by(Conversion.created_at.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
