from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_finance, require_super_admin
from app.core.errors import NotFoundError
from app.models.cvx import Campaign, CvxLedger, CvxRule
from app.models.user import User
from app.schemas import admin as s
from app.schemas import cvx as cs
from app.schemas.common import Paginated
from app.services import settings_service as settings
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/cvx/settings", response_model=list[cs.CvxRuleOut], dependencies=[Depends(require_finance)])
def cvx_settings(db: Session = Depends(get_db)):
    rows = db.query(CvxRule).order_by(CvxRule.section.asc(), CvxRule.key.asc()).all()
    if not rows:
        rows = _default_rules(db)
    return [cs.CvxRuleOut(key=r.key, value=r.value, kind=r.kind, label=r.label, section=r.section) for r in rows]


def _default_rules(db: Session) -> list[CvxRule]:
    defaults = {
        "cvx": [
            ("cvx.daily_limit", "5000", "number", "Daily earning limit", "cvx"),
            ("cvx.hourly_limit", "1000", "number", "Hourly earning limit", "cvx"),
            ("cvx.max_balance", "100000", "number", "Max CVX balance", "cvx"),
            ("cvx.global_multiplier", "1.0", "number", "Global reward multiplier", "cvx"),
            ("cvx.min_reward", "50", "number", "Minimum reward", "cvx"),
            ("cvx.max_reward", "100000", "number", "Maximum reward", "cvx"),
        ],
        "task": [
            ("tasks.offers_enabled", "true", "bool", "Offer wall enabled", "task"),
            ("tasks.tasks_enabled", "true", "bool", "Tasks enabled", "task"),
            ("tasks.max_daily_tasks", "100", "number", "Max daily tasks", "task"),
        ],
        "server": [
            ("minecraft.server_claims_enabled", "true", "bool", "Server claims enabled", "server"),
            ("minecraft.min_cvx", "2500", "number", "Minimum CVX to claim", "server"),
            ("minecraft.max_servers_per_user", "3", "number", "Max servers per user", "server"),
            ("minecraft.default_duration_days", "30", "number", "Default server duration (days)", "server"),
        ],
        "referral": [
            ("referral.enabled", "true", "bool", "Referrals enabled", "referral"),
            ("referral.reward", "250", "number", "Referral reward (CVX)", "referral"),
            ("referral.max_monthly", "10", "number", "Max referrals per month", "referral"),
        ],
    }
    created = []
    for section, items in defaults.items():
        for key, value, kind, label, sec in items:
            r = CvxRule(key=key, value=value, kind=kind, label=label, section=sec, public=True)
            db.add(r)
            created.append(r)
    db.commit()
    return created


@router.patch("/cvx/settings", response_model=dict, dependencies=[Depends(require_finance)])
def update_cvx_settings(payload: dict, db: Session = Depends(get_db)):
    values = payload.get("settings", {})
    for key, value in values.items():
        section = key.split(".")[0]
        settings.set_value(db, key, _coerce(value))
    return {"ok": True, "updated": list(values.keys())}


def _coerce(value: str):
    v = str(value)
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


@router.get("/cvx/ledger", response_model=Paginated[cs.LedgerEntry], dependencies=[Depends(require_finance)])
def ledger(
    user_id: str = "",
    txn_type: str = "",
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
):
    page, page_size = _page
    q = db.query(CvxLedger).order_by(CvxLedger.created_at.desc())
    if user_id:
        q = q.filter(CvxLedger.user_id == user_id)
    if txn_type:
        q = q.filter(CvxLedger.transaction_type == txn_type)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    rows = [
        cs.LedgerEntry(
            id=l.id, transaction_type=l.transaction_type, amount=l.amount, balance_after=l.balance_after,
            reference_type=l.reference_type, reference_id=l.reference_id, description=l.description,
            created_at=l.created_at,
        )
        for l in items
    ]
    return build_page(rows, total, page, page_size)


@router.get("/cvx/campaigns", response_model=list[dict], dependencies=[Depends(require_finance)])
def campaigns(db: Session = Depends(get_db)):
    rows = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return [
        {
            "id": c.id, "name": c.name, "multiplier": c.multiplier, "kind": c.kind,
            "applies_to": c.applies_to, "starts_at": c.starts_at, "ends_at": c.ends_at,
            "enabled": c.enabled, "description": c.description,
        }
        for c in rows
    ]


@router.post("/cvx/campaigns", response_model=dict, dependencies=[Depends(require_super_admin)])
def create_campaign(payload: s.CampaignCreate, db: Session = Depends(get_db)):
    c = Campaign(
        name=payload.name, multiplier=payload.multiplier, kind=payload.kind, applies_to=payload.applies_to,
        starts_at=payload.starts_at, ends_at=payload.ends_at, enabled=payload.enabled,
        description=payload.description,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"ok": True, "id": c.id}


@router.patch("/cvx/campaigns/{campaign_id}", response_model=dict, dependencies=[Depends(require_finance)])
def update_campaign(campaign_id: str, payload: s.CampaignCreate, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise NotFoundError("Campaign not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    return {"ok": True}
