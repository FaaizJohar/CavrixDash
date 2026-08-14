from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import misc as s
from app.schemas.common import Paginated
from app.services import notification_service
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Paginated[s.NotificationOut])
def list_notifications(
    unread_only: bool = False,
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page, page_size = _page
    items, total = notification_service.list_for_user(db, user.id, page, page_size, unread_only)
    rows = [
        s.NotificationOut(
            id=n.id,
            kind=n.kind,
            title=n.title,
            body=n.body,
            link=n.link,
            read=n.read,
            priority=n.priority,
            created_at=n.created_at,
        )
        for n in items
    ]
    return build_page(rows, total, page, page_size)


@router.post("/read", response_model=dict)
def mark_read(ids: list[str] | None = Body(default=None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = notification_service.mark_read(db, user.id, ids)
    return {"marked": count}
