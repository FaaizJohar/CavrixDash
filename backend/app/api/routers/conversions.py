from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.offer import Offer
from app.models.provider import Provider
from app.models.user import User
from app.schemas import cvx as s
from app.schemas.common import Paginated
from app.services import analytics_service
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/conversions", tags=["conversions"])


def _conv_out(c, offer: Offer | None, provider: Provider | None):
    return s.ConversionOut(
        id=c.id,
        click_id=c.click_id,
        offer_id=c.offer_id,
        offer_title=offer.title if offer else "",
        provider_code=provider.code if provider else "",
        conversion_id=c.conversion_id,
        status=c.status,
        reward_amount=c.reward_amount,
        risk_score=c.risk_score,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("", response_model=Paginated[s.ConversionOut])
def my_conversions(
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page, page_size = _page
    items, total = analytics_service.conversions_breakdown(db, user, page, page_size)
    offer_ids = [c.offer_id for c in items if c.offer_id]
    offers = {o.id: o for o in db.query(Offer).filter(Offer.id.in_(offer_ids)).all()} if offer_ids else {}
    provider_ids = {o.provider_id for o in offers.values()}
    providers = {p.id: p for p in db.query(Provider).filter(Provider.id.in_(provider_ids)).all()} if provider_ids else {}
    return build_page(
        [
            _conv_out(c, offers.get(c.offer_id), providers.get(offers.get(c.offer_id).provider_id) if offers.get(c.offer_id) else None)
            for c in items
        ],
        total, page, page_size,
    )
