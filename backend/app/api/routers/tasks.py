from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.models.offer import Offer
from app.models.provider import Provider
from app.models.user import User
from app.schemas import offer as s
from app.schemas.common import Paginated
from app.services import task_service
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_out(t, offer: Offer | None, provider: Provider | None):
    return s.TaskOut(
        id=t.id,
        click_id=t.click_id,
        offer_id=t.offer_id,
        offer_title=offer.title if offer else "",
        provider_code=provider.code if provider else "",
        category=offer.category if offer else "",
        reward_offered=t.reward_offered,
        status=t.status,
        risk_score=t.risk_score,
        external_tx_id=t.external_tx_id,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get("", response_model=Paginated[s.TaskOut])
def my_tasks(
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page, page_size = _page
    items, total = task_service.list_my_tasks(db, user.id, page, page_size)
    offer_ids = [t.offer_id for t in items if t.offer_id]
    offers = {o.id: o for o in db.query(Offer).filter(Offer.id.in_(offer_ids)).all()} if offer_ids else {}
    provider_ids = {o.provider_id for o in offers.values()}
    providers = {p.id: p for p in db.query(Provider).filter(Provider.id.in_(provider_ids)).all()} if provider_ids else {}
    return build_page(
        [
            _task_out(t, offers.get(t.offer_id), providers.get(offers.get(t.offer_id).provider_id) if offers.get(t.offer_id) else None)
            for t in items
        ],
        total, page, page_size,
    )


@router.get("/{click_id}", response_model=s.TaskOut)
def task_detail(click_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = task_service.get_click(db, click_id)
    if not t or t.user_id != user.id:
        raise NotFoundError("Task not found.")
    offer = db.query(Offer).filter(Offer.id == t.offer_id).first()
    provider = db.query(Provider).filter(Provider.id == offer.provider_id).first() if offer else None
    return _task_out(t, offer, provider)
