from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.cvx import CvxLedger
from app.models.user import User
from app.services import settings_service as settings

EARN_TYPES = {"CREDIT", "BONUS", "REFERRAL_REWARD"}
RESTORE_TYPES = {"REVERSAL", "REFUND"}
SPEND_TYPES = {"DEBIT", "SERVER_PURCHASE", "UPGRADE"}


def _commit(db: Session, user: User, ledger: CvxLedger) -> CvxLedger:
    db.add(ledger)
    user.cvx_balance = ledger.balance_after
    db.flush()
    db.commit()
    db.refresh(user)
    return ledger


def _lock_user(db: Session, user: User) -> User:
    """Re-read the user row with a row lock so balance math is race-free.

    SQLite ignores FOR UPDATE (single-writer); PostgreSQL locks the row so
    concurrent debits/credits serialize instead of double-spending.
    """
    locked = (
        db.query(User)
        .filter(User.id == user.id)
        .with_for_update()
        .first()
    )
    return locked or user


def get_balance(db: Session, user: User) -> float:
    return float(user.cvx_balance or 0.0)


def earned_in_window(db: Session, user_id: str, minutes: int) -> float:
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    total = (
        db.query(func.coalesce(func.sum(CvxLedger.amount), 0.0))
        .filter(
            CvxLedger.user_id == user_id,
            CvxLedger.transaction_type.in_(list(EARN_TYPES)),
            CvxLedger.created_at >= since,
            CvxLedger.amount > 0,
        )
        .scalar()
    )
    return float(total or 0.0)


def earned_today(db: Session, user_id: str) -> float:
    return earned_in_window(db, user_id, 24 * 60)


def earned_this_hour(db: Session, user_id: str) -> float:
    return earned_in_window(db, user_id, 60)


def credit(
    db: Session,
    user: User,
    amount: float,
    txn_type: str,
    description: str,
    *,
    reference_type: str = "",
    reference_id: str = "",
    meta: dict[str, Any] | None = None,
    created_by: str = "system",
    check_limits: bool = True,
    campaign_multiplier: float = 1.0,
) -> CvxLedger:
    if amount <= 0:
        raise AppError("Amount must be positive", code="INVALID_AMOUNT")
    amount = round(amount * campaign_multiplier, 2)

    user = _lock_user(db, user)

    if txn_type in EARN_TYPES and check_limits:
        daily = float(settings.get_value(db, "cvx.daily_limit", 5000))
        hourly = float(settings.get_value(db, "cvx.hourly_limit", 1000))
        max_bal = float(settings.get_value(db, "cvx.max_balance", 100000))
        if earned_today(db, user.id) + amount > daily:
            raise AppError(
                f"Daily earning limit of {daily:,.0f} reached. Come back tomorrow.",
                code="DAILY_LIMIT",
            )
        if earned_this_hour(db, user.id) + amount > hourly:
            raise AppError(
                f"Hourly earning limit of {hourly:,.0f} reached. Please wait.",
                code="HOURLY_LIMIT",
            )
        if user.cvx_balance + amount > max_bal:
            raise AppError(
                f"Wallet limit of {max_bal:,.0f} reached.", code="WALLET_LIMIT"
            )

    balance_after = round(user.cvx_balance + amount, 2)
    ledger = CvxLedger(
        user_id=user.id,
        transaction_type=txn_type,
        amount=round(amount, 2),
        balance_after=balance_after,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description[:400],
        meta=json.dumps(meta or {}, ensure_ascii=False),
        created_by=created_by,
    )
    if txn_type in EARN_TYPES:
        user.cvx_lifetime_earned = round((user.cvx_lifetime_earned or 0) + amount, 2)
    return _commit(db, user, ledger)


def debit(
    db: Session,
    user: User,
    amount: float,
    txn_type: str,
    description: str,
    *,
    reference_type: str = "",
    reference_id: str = "",
    meta: dict[str, Any] | None = None,
    created_by: str = "system",
) -> CvxLedger:
    if amount <= 0:
        raise AppError("Amount must be positive", code="INVALID_AMOUNT")

    user = _lock_user(db, user)

    if user.cvx_balance + 1e-9 < amount:
        raise AppError(
            "Insufficient CVX balance.", code="INSUFFICIENT_CVX"
        )
    balance_after = round(user.cvx_balance - amount, 2)
    ledger = CvxLedger(
        user_id=user.id,
        transaction_type=txn_type,
        amount=round(-amount, 2),
        balance_after=balance_after,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description[:400],
        meta=json.dumps(meta or {}, ensure_ascii=False),
        created_by=created_by,
    )
    if txn_type in SPEND_TYPES:
        user.cvx_lifetime_spent = round((user.cvx_lifetime_spent or 0) + amount, 2)
    return _commit(db, user, ledger)


def reversal(
    db: Session,
    user: User,
    amount: float,
    description: str,
    *,
    reference_type: str = "conversion",
    reference_id: str = "",
    meta: dict[str, Any] | None = None,
    created_by: str = "system",
) -> CvxLedger:
    return credit(
        db,
        user,
        abs(amount),
        "REVERSAL",
        description,
        reference_type=reference_type,
        reference_id=reference_id,
        meta=meta,
        created_by=created_by,
        check_limits=False,
    )


def refund(
    db: Session,
    user: User,
    amount: float,
    description: str,
    *,
    reference_type: str = "",
    reference_id: str = "",
    meta: dict[str, Any] | None = None,
    created_by: str = "system",
) -> CvxLedger:
    return credit(
        db,
        user,
        amount,
        "REFUND",
        description,
        reference_type=reference_type,
        reference_id=reference_id,
        meta=meta,
        created_by=created_by,
        check_limits=False,
    )


def adjust(
    db: Session,
    user: User,
    delta: float,
    reason: str,
    *,
    actor: str = "admin",
) -> CvxLedger:
    """Admin manual adjustment. delta can be positive or negative."""
    if delta > 0:
        return credit(
            db,
            user,
            delta,
            "ADJUSTMENT",
            reason[:400],
            reference_type="admin",
            created_by=actor,
            check_limits=False,
        )
    if delta < 0:
        amt = abs(delta)
        user = _lock_user(db, user)
        if user.cvx_balance + 1e-9 < amt:
            raise AppError("User does not have enough CVX for this adjustment.", code="INSUFFICIENT_CVX")
        return debit(db, user, amt, "ADJUSTMENT", reason[:400], reference_type="admin", created_by=actor)
    raise AppError("Delta cannot be zero.", code="INVALID_AMOUNT")


def ledger_for_user(
    db: Session, user_id: str, page: int = 1, page_size: int = 50
) -> tuple[list[CvxLedger], int]:
    q = db.query(CvxLedger).filter(CvxLedger.user_id == user_id).order_by(CvxLedger.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_wallet(db: Session, user: User) -> dict[str, Any]:
    return {
        "balance": round(user.cvx_balance or 0, 2),
        "lifetime_earned": round(user.cvx_lifetime_earned or 0, 2),
        "lifetime_spent": round(user.cvx_lifetime_spent or 0, 2),
        "daily_limit": float(settings.get_value(db, "cvx.daily_limit", 5000)),
        "hourly_limit": float(settings.get_value(db, "cvx.hourly_limit", 1000)),
        "max_balance": float(settings.get_value(db, "cvx.max_balance", 100000)),
        "earned_today": round(earned_today(db, user.id), 2),
        "earned_this_hour": round(earned_this_hour(db, user.id), 2),
    }
