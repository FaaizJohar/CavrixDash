from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import cvx as s
from app.schemas.common import Paginated
from app.services import cvx_service
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/cvx", tags=["cvx"])


@router.get("/wallet", response_model=s.WalletOut)
def wallet(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cvx_service.get_wallet(db, user)


@router.get("/ledger", response_model=Paginated[s.LedgerEntry])
def ledger(
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page, page_size = _page
    items, total = cvx_service.ledger_for_user(db, user.id, page, page_size)
    entries = [
        s.LedgerEntry(
            id=l.id,
            transaction_type=l.transaction_type,
            amount=l.amount,
            balance_after=l.balance_after,
            reference_type=l.reference_type,
            reference_id=l.reference_id,
            description=l.description,
            created_at=l.created_at,
        )
        for l in items
    ]
    return build_page(entries, total, page, page_size)


@router.get("/rules", response_model=list[s.CvxRuleOut])
def rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.models.cvx import CvxRule

    rows = db.query(CvxRule).filter(CvxRule.public == True).all()  # noqa: E712
    return [
        s.CvxRuleOut(key=r.key, value=r.value, kind=r.kind, label=r.label, section=r.section)
        for r in rows
    ]
