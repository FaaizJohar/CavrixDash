from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.models.support import SupportTicket, TicketMessage
from app.models.user import User
from app.schemas import misc as s
from app.schemas.common import Paginated
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/support", tags=["support"])


@router.get("/tickets", response_model=Paginated[s.TicketOut])
def my_tickets(
    _page: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page, page_size = _page
    q = (
        db.query(SupportTicket)
        .filter(SupportTicket.user_id == user.id)
        .order_by(SupportTicket.updated_at.desc())
    )
    total = q.count()
    tickets = q.offset((page - 1) * page_size).limit(page_size).all()
    rows = []
    for t in tickets:
        last = (
            db.query(TicketMessage)
            .filter(TicketMessage.ticket_id == t.id)
            .order_by(TicketMessage.created_at.desc())
            .first()
        )
        rows.append(
            s.TicketOut(
                id=t.id,
                subject=t.subject,
                category=t.category,
                status=t.status,
                priority=t.priority,
                created_at=t.created_at,
                updated_at=t.updated_at,
                last_message=last.body if last else "",
            )
        )
    return build_page(rows, total, page, page_size)


@router.post("/tickets", response_model=s.TicketDetail)
def create_ticket(payload: s.CreateTicketRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = SupportTicket(user_id=user.id, subject=payload.subject, category=payload.category)
    db.add(t)
    db.flush()
    msg = TicketMessage(ticket_id=t.id, sender_id=user.id, sender_role="user", body=payload.message)
    db.add(msg)
    db.commit()
    db.refresh(t)
    return s.TicketDetail(id=t.id, subject=t.subject, category=t.category, status=t.status, priority=t.priority, created_at=t.created_at)


@router.get("/tickets/{ticket_id}", response_model=s.TicketDetail)
def ticket_detail(ticket_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t or (t.user_id != user.id and not user.is_admin):
        raise NotFoundError("Ticket not found.")
    msgs = db.query(TicketMessage).filter(TicketMessage.ticket_id == t.id).order_by(TicketMessage.created_at.asc()).all()
    return s.TicketDetail(
        id=t.id,
        subject=t.subject,
        category=t.category,
        status=t.status,
        priority=t.priority,
        messages=[
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_role": m.sender_role,
                "body": m.body,
                "created_at": m.created_at,
            }
            for m in msgs
        ],
        created_at=t.created_at,
    )


@router.post("/tickets/{ticket_id}/messages", response_model=s.TicketDetail)
def reply(ticket_id: str, payload: s.CreateTicketMessageRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t or t.user_id != user.id:
        raise NotFoundError("Ticket not found.")
    msg = TicketMessage(ticket_id=t.id, sender_id=user.id, sender_role="user", body=payload.body)
    db.add(msg)
    if t.status in ("resolved", "closed"):
        t.status = "open"
    db.commit()
    return ticket_detail(ticket_id, db, user)
