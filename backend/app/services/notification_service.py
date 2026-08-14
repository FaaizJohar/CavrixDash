from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.notification import Notification


def push(
    db: Session,
    user_id: str,
    kind: str,
    title: str,
    body: str = "",
    *,
    link: str = "",
    priority: str = "normal",
    meta: dict[str, Any] | None = None,
) -> Notification:
    import json

    n = Notification(
        user_id=user_id,
        kind=kind,
        title=title[:200],
        body=body,
        link=link,
        priority=priority,
        meta=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(n)
    db.flush()
    return n


def list_for_user(
    db: Session, user_id: str, page: int = 1, page_size: int = 30, unread_only: bool = False
) -> tuple[list[Notification], int]:
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def mark_read(db: Session, user_id: str, ids: list[str] | None = None) -> int:
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if ids:
        q = q.filter(Notification.id.in_(ids))
    count = q.update({Notification.read: True}, synchronize_session=False)
    db.commit()
    return count


def unread_count(db: Session, user_id: str) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.read == False)  # noqa: E712
        .count()
    )
