from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_dashboard
from app.models.cvx import CvxLedger
from app.models.fraud import FraudEvent
from app.models.server import UserServer
from app.models.tracking import Conversion, TaskClick
from app.models.user import User
from app.schemas import admin as s

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_dashboard)])


@router.get("/overview", response_model=s.AdminOverview)
def overview(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_revenue = float(
        db.query(func.coalesce(func.sum(Conversion.payout_amount), 0.0))
        .filter(Conversion.status == "approved")
        .scalar() or 0.0
    )

    today_revenue = float(
        db.query(func.coalesce(func.sum(Conversion.payout_amount), 0.0))
        .filter(Conversion.status == "approved", Conversion.created_at >= today)
        .scalar() or 0.0
    )

    users_total = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.status == "active").scalar() or 0
    active_servers = db.query(func.count(UserServer.id)).filter(UserServer.status.in_(["running", "provisioning"])).scalar() or 0
    tasks = db.query(func.count(TaskClick.id)).scalar() or 0
    approved = db.query(func.count(Conversion.id)).filter(Conversion.status == "approved").scalar() or 0
    rejected = db.query(func.count(Conversion.id)).filter(Conversion.status == "rejected").scalar() or 0
    reversed_ = db.query(func.count(Conversion.id)).filter(Conversion.status == "reversed").scalar() or 0
    cvx_issued = float(db.query(func.coalesce(func.sum(CvxLedger.amount), 0.0)).filter(CvxLedger.transaction_type.in_(["CREDIT", "BONUS", "REFERRAL_REWARD"])).scalar() or 0.0)
    cvx_spent = float(db.query(func.coalesce(func.sum(-CvxLedger.amount), 0.0)).filter(CvxLedger.transaction_type.in_(["DEBIT", "SERVER_PURCHASE", "UPGRADE"])).scalar() or 0.0)
    cvx_outstanding = float(db.query(func.coalesce(func.sum(User.cvx_balance), 0.0)).scalar() or 0.0)
    risk = db.query(func.count(FraudEvent.id)).filter(FraudEvent.created_at >= now - timedelta(hours=24)).scalar() or 0

    # provider revenue (top 6)
    provider_rows = (
        db.query(Conversion.provider_id, func.sum(Conversion.payout_amount).label("rev"), func.count(Conversion.id).label("n"))
        .filter(Conversion.status == "approved")
        .group_by(Conversion.provider_id)
        .order_by(func.sum(Conversion.payout_amount).desc())
        .limit(6)
        .all()
    )
    from app.models.provider import Provider

    provider_revenue = []
    for pid, rev, n in provider_rows:
        p = db.query(Provider).filter(Provider.id == pid).first()
        provider_revenue.append({"name": p.name if p else pid, "revenue": float(rev or 0), "conversions": int(n)})

    # 7d revenue series (approved conversion payouts) with CVX credits for reference
    days = []
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        d_end = d + timedelta(days=1)
        payout = float(
            db.query(func.coalesce(func.sum(Conversion.payout_amount), 0.0))
            .filter(Conversion.status == "approved", Conversion.created_at >= d, Conversion.created_at < d_end)
            .scalar() or 0.0
        )
        cvx = float(
            db.query(func.coalesce(func.sum(CvxLedger.amount), 0.0))
            .filter(CvxLedger.transaction_type == "CREDIT", CvxLedger.created_at >= d, CvxLedger.created_at < d_end)
            .scalar() or 0.0
        )
        days.append({"label": d.strftime("%d %b"), "revenue": round(payout, 2), "cvx": round(cvx, 2), "cost": 0.0})

    return s.AdminOverview(
        total_revenue=round(total_revenue, 2),
        today_revenue=round(today_revenue, 2),
        pending_revenue=round(
            float(
                db.query(func.coalesce(func.sum(Conversion.payout_amount), 0.0))
                .filter(Conversion.status.in_(["pending", "held"]))
                .scalar() or 0.0
            ),
            2,
        ),
        users=users_total,
        active_users=active_users,
        active_servers=active_servers,
        tasks_completed=tasks,
        approved=approved,
        rejected=rejected,
        reversed=reversed_,
        cvx_issued=round(cvx_issued, 2),
        cvx_spent=round(cvx_spent, 2),
        cvx_outstanding=round(cvx_outstanding, 2),
        provider_revenue=provider_revenue,
        revenue_7d=days,
        risk_events_24h=risk,
    )


@router.get("/kpis")
def kpis(db: Session = Depends(get_db)):
    data = overview(db)
    return {
        "kpis": [
            {"key": "total_revenue", "label": "Total Revenue", "value": data.total_revenue},
            {"key": "today_revenue", "label": "Today", "value": data.today_revenue},
            {"key": "users", "label": "Users", "value": data.users},
            {"key": "active_servers", "label": "Active Servers", "value": data.active_servers},
            {"key": "tasks_completed", "label": "Tasks Completed", "value": data.tasks_completed},
            {"key": "approved", "label": "Conversions Approved", "value": data.approved},
            {"key": "cvx_issued", "label": "CVX Issued", "value": data.cvx_issued},
            {"key": "risk_events_24h", "label": "Risk Events (24h)", "value": data.risk_events_24h},
        ]
    }
