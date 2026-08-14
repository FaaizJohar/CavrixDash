from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class SupportTicket(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "support_tickets"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="general")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    # open | pending | resolved | closed
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    assigned_to: Mapped[str] = mapped_column(String(36), default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")


class TicketMessage(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "ticket_messages"

    ticket_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    sender_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    sender_role: Mapped[str] = mapped_column(String(20), default="user")  # user|admin|support|system
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachment: Mapped[str] = mapped_column(String(512), default="")
