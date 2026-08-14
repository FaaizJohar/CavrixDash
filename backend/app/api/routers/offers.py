from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_client_meta, get_current_user
from app.models.offer import Offer
from app.models.provider import Provider
from app.models.user import User
from app.schemas import offer as s
from app.schemas.common import Paginated
from app.services import task_service
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/offers", tags=["offers"])


def _provider_map(db: Session) -> dict[str, Provider]:
    return {p.id: p for p in db.query(Provider).all()}


def _offer_out(o: Offer, providers: dict[str, Provider]) -> dict:
    p = providers.get(o.provider_id)
    return {
        "id": o.id,
        "provider_code": p.code if p else "",
        "provider_name": p.name if p else "",
        "provider_kind": p.kind if p else "",
        "title": o.title,
        "description": o.description,
        "category": o.category,
        "icon_url": o.icon_url,
        "reward": o.reward,
        "estimated_time": o.estimated_time,
        "countries": _parse_list(o.countries),
        "devices": _parse_list(o.devices),
        "requirements": o.requirements,
        "conversion_event": o.conversion_event,
        "featured": o.featured,
        "priority": o.priority,
        "status": o.status,
        "conversion_rate": o.conversion_rate,
        "approval_rate": o.approval_rate,
        "completion_count": o.completion_count,
        "effective_reward": o.effective_reward,
        "click_url": o.click_url,
        "starts_at": o.starts_at,
        "expires_at": o.expires_at,
        "created_at": o.created_at,
        "updated_at": o.updated_at,
    }


def _parse_list(raw: str) -> list[str]:
    try:
        val = json.loads(raw or "[]")
        return val if isinstance(val, list) else []
    except (ValueError, TypeError):
        return []


@router.get("", response_model=Paginated[s.OfferOut])
def offer_feed(
    category: str | None = None,
    sort: str = "recommended",
    device: str | None = None,
    country: str | None = None,
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
):
    page, page_size = _page
    items, total = task_service.list_offers(
        db, category=category, sort=sort, device=device, country=country, page=page, page_size=page_size
    )
    providers = _provider_map(db)
    return build_page([_offer_out(o, providers) for o in items], total, page, page_size)


@router.get("/{offer_id}", response_model=s.OfferDetail)
def offer_detail(offer_id: str, db: Session = Depends(get_db)):
    from app.core.errors import NotFoundError

    o = task_service.get_offer(db, offer_id)
    if o.status != "active":
        raise NotFoundError("Offer not found.")
    data = _offer_out(o, _provider_map(db))
    data["landing_url"] = o.landing_url or o.click_url
    return data


@router.post("/{offer_id}/click", response_model=s.ClickResponse)
def click_offer(offer_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.core.rate_limit import hit as rate_hit
    from app.core.config import settings

    rate_hit("offers", user.id, settings.rate_limit_general_per_min)
    o = task_service.get_offer(db, offer_id)
    if o.status != "active":
        from app.core.errors import NotFoundError

        raise NotFoundError("Offer not found.")
    meta = get_client_meta(request)
    click = task_service.create_click(
        db, user, o, ip=meta["ip"], user_agent=meta["user_agent"], device_id=meta["device_id"]
    )
    return s.ClickResponse(click_id=click.click_id, redirect_url=click.redirect_url, expires_in=120)
