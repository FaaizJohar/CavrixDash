from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import referral as s
from app.schemas.common import Paginated
from app.services import referral_service
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("", response_model=s.ReferralSummary)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return referral_service.summary(db, user)


@router.get("/invitees", response_model=Paginated[s.ReferralRow])
def invitees(
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page, page_size = _page
    items, total = referral_service.rows(db, user.id, page, page_size)
    rows = [
        s.ReferralRow(
            id=r.id,
            invitee_email=r.invitee_email,
            status=r.status,
            reward_amount=r.reward_amount,
            rewarded_at=r.rewarded_at,
            risk_score=r.risk_score,
            created_at=r.created_at,
        )
        for r in items
    ]
    return build_page(rows, total, page, page_size)
