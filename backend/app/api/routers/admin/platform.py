from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    require_admin,
    require_finance,
    require_infra,
    require_staff,
    require_super_admin,
    verify_step_up,
)
from app.models.cvx import CvxLedger
from app.models.fraud import FraudEvent, FraudRule
from app.models.notification import Announcement
from app.models.server import UserServer
from app.models.support import SupportTicket
from app.models.tracking import Conversion
from app.models.user import User
from app.schemas import admin as s
from app.schemas.common import Paginated
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/revenue", response_model=dict, dependencies=[Depends(require_finance)])
def revenue(db: Session = Depends(get_db)):
    total = float(
        db.query(func.coalesce(func.sum(Conversion.payout_amount), 0.0))
        .filter(Conversion.status == "approved")
        .scalar() or 0.0
    )
    pending = float(
        db.query(func.coalesce(func.sum(Conversion.payout_amount), 0.0))
        .filter(Conversion.status == "held")
        .scalar() or 0.0
    )
    paid = float(
        db.query(func.coalesce(func.sum(Conversion.payout_amount), 0.0))
        .filter(Conversion.status == "approved")
        .scalar() or 0.0
    )
    by_provider = []
    from app.models.provider import Provider

    rows = (
        db.query(Conversion.provider_id, func.sum(Conversion.payout_amount).label("rev"))
        .filter(Conversion.status == "approved")
        .group_by(Conversion.provider_id)
        .order_by(func.sum(Conversion.payout_amount).desc())
        .all()
    )
    for pid, rev in rows:
        p = db.query(Provider).filter(Provider.id == pid).first()
        by_provider.append({"provider": p.code if p else pid, "revenue": float(rev or 0)})

    payouts = []  # payout requests flow through support/adjustments
    return {"total": round(total, 2), "today": 0, "pending": round(pending, 2), "paid": round(paid, 2), "by_provider": by_provider, "payouts": payouts}


@router.get("/analytics", response_model=dict, dependencies=[Depends(require_finance)])
def analytics(db: Session = Depends(get_db)):
    return {"series": []}


@router.get("/fraud/events", response_model=Paginated[dict], dependencies=[Depends(require_staff)])
def fraud_events(_page: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)):
    page, page_size = _page
    q = db.query(FraudEvent).order_by(FraudEvent.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    rows = [
        {
            "id": e.id, "user_id": e.user_id, "event_type": e.event_type, "severity": e.severity,
            "description": e.description, "details": e.meta, "created_at": e.created_at,
        }
        for e in items
    ]
    return build_page(rows, total, page, page_size)


@router.get("/fraud/users", response_model=Paginated[s.AdminUserRow], dependencies=[Depends(require_staff)])
def fraud_users(_page: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)):
    page, page_size = _page
    q = db.query(User).filter(User.risk_score >= 20).order_by(User.risk_score.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    rows = [
        s.AdminUserRow(
            id=u.id, email=u.email, username=u.username, display_name=u.display_name,
            email_verified=u.email_verified, twofa_enabled=u.twofa_enabled, status=u.status,
            risk_score=u.risk_score, cvx_balance=u.cvx_balance, tasks_completed=u.tasks_completed,
            conversions_approved=u.conversions_approved, roles=[r.name for r in u.roles], created_at=u.created_at,
        )
        for u in items
    ]
    return build_page(rows, total, page, page_size)


@router.get("/fraud/rules", response_model=list[dict], dependencies=[Depends(require_staff)])
def fraud_rules(db: Session = Depends(get_db)):
    rows = db.query(FraudRule).order_by(FraudRule.key.asc()).all()
    return [
        {"key": r.key, "label": r.label or r.key, "value": r.value, "description": r.description}
        for r in rows
    ]


@router.patch("/fraud/rules", response_model=dict, dependencies=[Depends(require_admin)])
def update_fraud_rules(payload: s.FraudRuleUpdate, db: Session = Depends(get_db)):
    for key, value in payload.rules.items():
        row = db.query(FraudRule).filter(FraudRule.key == key).first()
        if row:
            row.value = str(value)
    db.commit()
    return {"ok": True}


@router.get("/announcements", response_model=Paginated[dict], dependencies=[Depends(require_staff)])
def announcements(_page: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)):
    page, page_size = _page
    q = db.query(Announcement).order_by(Announcement.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    rows = [
        {
            "id": a.id, "title": a.title, "message": a.message, "audience": a.audience,
            "priority": a.priority, "starts_at": a.starts_at, "ends_at": a.ends_at,
            "enabled": a.enabled, "created_at": a.created_at,
        }
        for a in items
    ]
    return build_page(rows, total, page, page_size)


@router.post("/announcements", response_model=dict, dependencies=[Depends(require_admin)])
def create_announcement(payload: s.AnnouncementCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    a = Announcement(
        title=payload.title, message=payload.message, audience=payload.audience,
        priority=payload.priority, starts_at=payload.starts_at, ends_at=payload.ends_at,
        enabled=payload.enabled, created_by=admin.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"ok": True, "id": a.id}


@router.patch("/announcements/{announcement_id}", response_model=dict, dependencies=[Depends(require_admin)])
def update_announcement(announcement_id: str, payload: dict, db: Session = Depends(get_db)):
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a:
        from app.core.errors import NotFoundError

        raise NotFoundError("Announcement not found.")
    for k, v in payload.items():
        if hasattr(a, k):
            setattr(a, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/announcements/{announcement_id}", response_model=dict, dependencies=[Depends(require_admin)])
def delete_announcement(announcement_id: str, db: Session = Depends(get_db)):
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if a:
        db.delete(a)
        db.commit()
    return {"ok": True}


@router.get("/support", response_model=Paginated[dict], dependencies=[Depends(require_staff)])
def support_queue(status: str = "open", _page: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)):
    from app.models.support import TicketMessage

    page, page_size = _page
    q = db.query(SupportTicket)
    if status and status != "all":
        q = q.filter(SupportTicket.status == status)
    q = q.order_by(SupportTicket.updated_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    rows = []
    for t in items:
        last = (
            db.query(TicketMessage)
            .filter(TicketMessage.ticket_id == t.id)
            .order_by(TicketMessage.created_at.desc())
            .first()
        )
        rows.append(
            {
                "id": t.id, "subject": t.subject, "category": t.category, "status": t.status,
                "priority": t.priority, "created_at": t.created_at, "updated_at": t.updated_at,
                "last_message": last.body if last else "",
            }
        )
    return build_page(rows, total, page, page_size)


@router.patch("/support/{ticket_id}", response_model=dict, dependencies=[Depends(require_staff)])
def update_ticket(ticket_id: str, payload: dict, db: Session = Depends(get_db)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        from app.core.errors import NotFoundError

        raise NotFoundError("Ticket not found.")
    for k, v in payload.items():
        if hasattr(t, k):
            setattr(t, k, v)
    db.commit()
    return {"ok": True}


@router.get("/audit", response_model=Paginated[s.AuditRow], dependencies=[Depends(require_super_admin)])
def audit(category: str = "", q: str = "", _page: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)):
    from app.models.audit import AuditLog

    page, page_size = _page
    qr = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if category:
        qr = qr.filter(AuditLog.category == category)
    if q:
        qr = qr.filter(AuditLog.actor_name.ilike(f"%{q}%"))
    total = qr.count()
    items = qr.offset((page - 1) * page_size).limit(page_size).all()
    rows = [s.AuditRow.model_validate(a, from_attributes=True) for a in items]
    return build_page(rows, total, page, page_size)


@router.get("/servers", response_model=Paginated[dict], dependencies=[Depends(require_infra)])
def all_servers(status: str = "", _page: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)):
    page, page_size = _page
    q = db.query(UserServer).order_by(UserServer.created_at.desc())
    if status:
        q = q.filter(UserServer.status == status)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    rows = [
        {
            "id": srv.id, "name": srv.name, "user_id": srv.user_id, "region": srv.region,
            "status": srv.status, "software": srv.software, "version": srv.version,
            "ram_mb": srv.ram_mb, "cpu": srv.cpu, "disk_mb": srv.disk_mb,
            "expires_at": srv.expires_at, "created_at": srv.created_at,
        }
        for srv in items
    ]
    return build_page(rows, total, page, page_size)


@router.delete("/servers/{server_id}", response_model=dict)
def destroy_server(server_id: str, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_super_admin)):
    verify_step_up(request, admin)
    from app.services import server_service

    srv = db.query(UserServer).filter(UserServer.id == server_id).first()
    if not srv:
        from app.core.errors import NotFoundError

        raise NotFoundError("Server not found.")
    server_service.destroy_server(db, srv)
    return {"ok": True}
