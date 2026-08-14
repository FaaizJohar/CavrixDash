from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    get_client_meta,
    require_admin,
    require_finance,
    require_staff,
    require_super_admin,
    verify_step_up,
)
from app.core.errors import ForbiddenError, NotFoundError
from app.models.offer import Offer
from app.models.provider import Provider
from app.models.server import UserServer
from app.models.tracking import Conversion, TaskClick
from app.models.user import Role, User
from app.schemas import admin as s
from app.schemas import offer as os
from app.schemas.common import Paginated
from app.services import audit_service, cvx_service, user_service
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/admin", tags=["admin"])


def _row(u: User, db: Session) -> s.AdminUserRow:
    return s.AdminUserRow(
        id=u.id,
        email=u.email,
        username=u.username,
        display_name=u.display_name,
        email_verified=u.email_verified,
        twofa_enabled=u.twofa_enabled,
        status=u.status,
        risk_score=u.risk_score,
        cvx_balance=u.cvx_balance,
        tasks_completed=u.tasks_completed,
        conversions_approved=u.conversions_approved,
        active_servers=db.query(UserServer).filter(UserServer.user_id == u.id, UserServer.status == "running").count(),
        roles=[r.name for r in u.roles],
        created_at=u.created_at,
    )


@router.get("/users", response_model=Paginated[s.AdminUserRow], dependencies=[Depends(require_staff)])
def users(
    search: str = "",
    status: str = "",
    sort: str = "created_at",
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
):
    page, page_size = _page
    items, total = user_service.list_users(db, search=search, status=status, sort=sort, page=page, page_size=page_size)
    return build_page([_row(u, db) for u in items], total, page, page_size)


@router.patch("/users/{user_id}", response_model=s.AdminUserRow, dependencies=[Depends(require_admin)])
def update_user(user_id: str, payload: s.AdminUserUpdate, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = user_service.get_by_id(db, user_id)
    if not u:
        raise NotFoundError("User not found.")

    is_super = admin.has_role("super_admin")
    target_is_super = u.has_role("super_admin")

    # Authorization is checked before step-up so a low-privilege caller gets
    # FORBIDDEN rather than leaking that step-up exists.
    if payload.roles is not None and not is_super:
        raise ForbiddenError("Only super admins can modify roles.", code="FORBIDDEN")
    if payload.status is not None and target_is_super and not is_super:
        raise ForbiddenError("Only super admins can modify super admin accounts.", code="FORBIDDEN")

    # Role changes and CVX adjustments are sensitive: require a fresh
    # password (+2FA) confirmation before applying them.
    if payload.roles is not None or payload.cvx_adjustment not in (None, 0):
        verify_step_up(request, admin)

    if payload.roles is not None:
        roles = [db.query(Role).filter(Role.name == r).first() for r in payload.roles]
        u.roles = [r for r in roles if r]
    if payload.status is not None:
        u.status = payload.status
    if payload.max_servers is not None:
        meta = json.loads(u.meta or "{}")
        meta["max_servers"] = payload.max_servers
        u.meta = json.dumps(meta)
    if payload.cvx_adjustment not in (None, 0):
        cvx_service.adjust(db, u, payload.cvx_adjustment, payload.cvx_adjustment_reason or "Admin adjustment", actor=admin.email)

    db.commit()
    db.refresh(u)
    audit_service.log_audit(db, actor_id=admin.id, actor_name=admin.email, action="user.update",
                            category="user", target_type="user", target_id=u.id,
                            ip=get_client_meta(request)["ip"] if request else "")
    return _row(u, db)


@router.get("/providers", response_model=Paginated[s.ProviderOut], dependencies=[Depends(require_finance)])
def providers(_page: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)):
    from app.models.provider import Provider
    from app.services import provider_service

    page, page_size = _page
    rows = provider_service.list_providers(db)
    total = len(rows)
    items = rows[(page - 1) * page_size : page * page_size]
    out = []
    for p in items:
        out.append(
            s.ProviderOut(
                id=p.id,
                code=p.code,
                name=p.name,
                kind=p.kind,
                enabled=p.enabled,
                status=p.status,
                priority=p.priority,
                reward_multiplier=p.reward_multiplier,
                reliability=p.reliability,
                revenue_tracked=p.revenue_tracked,
                last_synced_at=p.last_synced_at,
                last_error=p.last_error,
                credentials_masked=provider_service.masked_credentials(db, p.id),
                meta=json.loads(p.meta or "{}"),
                created_at=p.created_at,
            )
        )
    return build_page(out, total, page, page_size)


@router.post("/providers", response_model=s.ProviderOut, dependencies=[Depends(require_super_admin)])
def create_provider(payload: s.ProviderCreate, db: Session = Depends(get_db)):
    from app.services import provider_service

    p = provider_service.create_provider(db, payload.model_dump())
    return s.ProviderOut(
        id=p.id, code=p.code, name=p.name, kind=p.kind, enabled=p.enabled, status=p.status,
        priority=p.priority, reward_multiplier=p.reward_multiplier, reliability=p.reliability,
        revenue_tracked=p.revenue_tracked, last_synced_at=p.last_synced_at, last_error=p.last_error,
        credentials_masked=provider_service.masked_credentials(db, p.id), meta=json.loads(p.meta or "{}"),
        created_at=p.created_at,
    )


@router.patch("/providers/{provider_id}", response_model=s.ProviderOut, dependencies=[Depends(require_finance)])
def update_provider(provider_id: str, payload: s.ProviderUpdate, db: Session = Depends(get_db)):
    from app.services import provider_service

    p = provider_service.get_provider(db, provider_id)
    p = provider_service.update_provider(db, p, payload.model_dump(exclude_unset=True))
    return s.ProviderOut(
        id=p.id, code=p.code, name=p.name, kind=p.kind, enabled=p.enabled, status=p.status,
        priority=p.priority, reward_multiplier=p.reward_multiplier, reliability=p.reliability,
        revenue_tracked=p.revenue_tracked, last_synced_at=p.last_synced_at, last_error=p.last_error,
        credentials_masked=provider_service.masked_credentials(db, p.id), meta=json.loads(p.meta or "{}"),
        created_at=p.created_at,
    )


@router.delete("/providers/{provider_id}", dependencies=[Depends(require_super_admin)])
def delete_provider(provider_id: str, db: Session = Depends(get_db)):
    from app.models.provider import Provider
    from app.services import provider_service

    p = provider_service.get_provider(db, provider_id)
    db.delete(p)
    db.commit()
    return {"message": "Provider deleted."}


@router.post("/providers/{provider_id}/test", response_model=dict, dependencies=[Depends(require_finance)])
def test_provider(provider_id: str, db: Session = Depends(get_db)):
    from app.services import provider_service

    p = provider_service.get_provider(db, provider_id)
    return provider_service.test_connection(db, p)


@router.post("/providers/{provider_id}/sync", response_model=dict, dependencies=[Depends(require_finance)])
def sync_provider(provider_id: str, db: Session = Depends(get_db)):
    from app.services import provider_service

    p = provider_service.get_provider(db, provider_id)
    count = provider_service.sync_offers(db, p)
    return {"synced": count, "provider": p.code}


@router.post("/providers/sync-all", response_model=dict, dependencies=[Depends(require_super_admin)])
def sync_all(db: Session = Depends(get_db)):
    from app.services import provider_service

    total = 0
    for p in provider_service.list_providers(db):
        if not p.enabled:
            continue
        try:
            total += provider_service.sync_offers(db, p)
        except Exception:
            continue
    return {"synced": total}


@router.get("/offers", response_model=Paginated[os.OfferOut], dependencies=[Depends(require_finance)])
def offers(
    status: str = "",
    search: str = "",
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
):
    from app.models.offer import Offer
    from app.models.provider import Provider

    page, page_size = _page
    q = db.query(Offer).join(Provider, Offer.provider_id == Provider.id)
    if status:
        q = q.filter(Offer.status == status)
    if search:
        q = q.filter(Offer.title.ilike(f"%{search}%"))
    q = q.order_by(Offer.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    provider_map = {p.id: p for p in db.query(Provider).all()}
    out = []
    for o in items:
        p = provider_map.get(o.provider_id)
        out.append(
            os.OfferOut(
                id=o.id, provider_code=p.code if p else "", provider_name=p.name if p else "",
                provider_kind=p.kind if p else "", title=o.title, description=o.description,
                category=o.category, icon_url=o.icon_url, reward=o.reward, estimated_time=o.estimated_time,
                countries=json.loads(o.countries or "[]"), devices=json.loads(o.devices or "[]"),
                requirements=o.requirements, conversion_event=o.conversion_event, featured=o.featured,
                priority=o.priority, status=o.status, conversion_rate=o.conversion_rate,
                approval_rate=o.approval_rate, completion_count=o.completion_count,
                effective_reward=o.effective_reward, click_url=o.click_url,
                starts_at=o.starts_at, expires_at=o.expires_at, created_at=o.created_at,
            )
        )
    return build_page(out, total, page, page_size)


@router.patch("/offers/{offer_id}", response_model=os.OfferOut, dependencies=[Depends(require_finance)])
def update_offer(offer_id: str, payload: s.OfferUpdate, db: Session = Depends(get_db)):
    from app.models.offer import Offer
    from app.models.provider import Provider

    o = db.query(Offer).filter(Offer.id == offer_id).first()
    if not o:
        raise NotFoundError("Offer not found.")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k in ("countries", "devices"):
            o.__setattr__(k, json.dumps(v))
        else:
            o.__setattr__(k, v)
    db.commit()
    db.refresh(o)
    p = db.query(Provider).filter(Provider.id == o.provider_id).first()
    return os.OfferOut(
        id=o.id, provider_code=p.code if p else "", provider_name=p.name if p else "",
        provider_kind=p.kind if p else "", title=o.title, description=o.description,
        category=o.category, icon_url=o.icon_url, reward=o.reward, estimated_time=o.estimated_time,
        countries=json.loads(o.countries or "[]"), devices=json.loads(o.devices or "[]"),
        requirements=o.requirements, conversion_event=o.conversion_event, featured=o.featured,
        priority=o.priority, status=o.status, conversion_rate=o.conversion_rate,
        approval_rate=o.approval_rate, completion_count=o.completion_count,
        effective_reward=o.effective_reward, click_url=o.click_url,
        starts_at=o.starts_at, expires_at=o.expires_at, created_at=o.created_at,
    )


@router.get("/conversions", response_model=Paginated[dict], dependencies=[Depends(require_finance)])
def conversions(
    status: str = "",
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
):
    page, page_size = _page
    q = db.query(Conversion).order_by(Conversion.created_at.desc())
    if status:
        q = q.filter(Conversion.status == status)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    out = []
    for c in items:
        u = db.query(User).filter(User.id == c.user_id).first()
        out.append({
            "id": c.id, "click_id": c.click_id, "offer_id": c.offer_id,
            "user_email": u.email if u else "",
            "conversion_id": c.conversion_id, "status": c.status,
            "reward_amount": c.reward_amount, "payout_amount": c.payout_amount,
            "risk_score": c.risk_score, "reviewed_by": c.reviewed_by,
            "created_at": c.created_at, "updated_at": c.updated_at,
        })
    return build_page(out, total, page, page_size)


@router.patch("/conversions/{conversion_id}", response_model=dict, dependencies=[Depends(require_finance)])
def review_conversion(conversion_id: str, payload: s.ConversionAdminUpdate, db: Session = Depends(get_db), admin: User = Depends(require_finance)):
    from app.services import conversion_service, cvx_service
    from app.services import notification_service

    c = db.query(Conversion).filter(Conversion.id == conversion_id).first()
    if not c:
        raise NotFoundError("Conversion not found.")
    old_status = c.status
    if payload.status in ("approved", "rejected", "reversed", "held"):
        if payload.status == "approved" and c.status != "approved":
            offer = db.query(Offer).filter(Offer.id == c.offer_id).first()
            provider = db.query(Provider).filter(Provider.id == c.provider_id).first()
            reward = conversion_service.compute_reward(db, offer, provider) if offer and provider else c.reward_amount
            u = db.query(User).filter(User.id == c.user_id).first()
            if u:
                cvx_service.credit(db, u, reward, "CREDIT", "Manual approval", reference_type="conversion", reference_id=c.id, created_by="admin")
                u.conversions_approved += 1
                u.tasks_completed += 1
                notification_service.push(db, u.id, "conversion_approved", "Reward approved", f"{reward:,.0f} CVX credited.", link="/rewards")
            c.reward_amount = reward
            db.query(TaskClick).filter(TaskClick.click_id == c.click_id).update({"status": "approved"})
        elif payload.status == "rejected":
            u = db.query(User).filter(User.id == c.user_id).first()
            db.query(TaskClick).filter(TaskClick.click_id == c.click_id).update({"status": "rejected"})
            if u:
                notification_service.push(db, u.id, "conversion_rejected", "Conversion rejected", payload.review_note or "Review failed.", link="/earn/my-tasks")
        c.status = payload.status
        c.reviewed_by = admin.email
        c.reviewed_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"ok": True, "id": c.id, "status": c.status, "old_status": old_status}
