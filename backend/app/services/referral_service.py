from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.referral import Referral
from app.models.user import User
from app.services import cvx_service, settings_service as settings
from app.services import notification_service


def create_referral(db: Session, referrer: User, invitee: User, ip: str) -> Referral:
    existing = db.query(Referral).filter(Referral.invitee_id == invitee.id).first()
    if existing:
        return existing
    ref = Referral(
        referrer_id=referrer.id,
        invitee_id=invitee.id,
        invitee_email=invitee.email,
        status="pending",
        source_ip=ip,
    )
    db.add(ref)
    db.flush()
    return ref


def on_invitee_verified(db: Session, invitee: User) -> None:
    """Called when invitee reaches the verification milestone (e.g. first approved conversion)."""
    if not settings.get_value(db, "referral.enabled", True):
        return
    if not invitee.invited_by:
        return
    ref = (
        db.query(Referral)
        .filter(Referral.invitee_id == invitee.id, Referral.status == "pending")
        .first()
    )
    if not ref:
        return
    referrer = db.query(User).filter(User.id == ref.referrer_id).first()
    if not referrer:
        return

    verification_required = settings.get_value(db, "referral.verification_required", True)
    if verification_required and not invitee.email_verified:
        return

    max_monthly = int(settings.get_value(db, "referral.max_monthly", 10))
    month_start = datetime.now(timezone.utc).replace(day=1).isoformat()
    month_count = (
        db.query(Referral)
        .filter(
            Referral.referrer_id == referrer.id,
            Referral.status.in_(["rewarded", "verified"]),
            Referral.rewarded_at >= month_start,
        )
        .count()
    )
    if month_count >= max_monthly:
        return

    reward = float(settings.get_value(db, "referral.reward", 250))
    campaign_mult = float(settings.get_value(db, "referral.campaign_multiplier", 1.0))
    reward = round(reward * campaign_mult, 2)

    # anti-abuse: same device/IP farming check (basic)
    if ref.risk_score >= float(settings.get_value(db, "referral.anti_abuse_threshold", 3) * 10):
        ref.status = "rejected"
        db.commit()
        return

    try:
        cvx_service.credit(
            db,
            referrer,
            reward,
            "REFERRAL_REWARD",
            f"Referral reward for {invitee.username}",
            reference_type="referral",
            reference_id=ref.id,
            meta={"invitee_id": invitee.id},
        )
    except AppError:
        return

    ref.status = "rewarded"
    ref.reward_amount = reward
    ref.rewarded_at = datetime.now(timezone.utc).isoformat()
    referrer.referral_cvx_earned = round((referrer.referral_cvx_earned or 0) + reward, 2)
    notification_service.push(
        db,
        referrer.id,
        "referral_reward",
        "Referral reward earned",
        f"You earned {reward:,.0f} CVX from your referral {invitee.username}.",
        link="/referrals",
    )
    db.commit()


def summary(db: Session, user: User) -> dict[str, Any]:
    refs = db.query(Referral).filter(Referral.referrer_id == user.id).all()
    month_start = datetime.now(timezone.utc).replace(day=1).isoformat()
    this_month = sum(1 for r in refs if (r.rewarded_at or "") >= month_start)
    return {
        "code": user.referral_code,
        "url": f"{settings_env().frontend_url}/auth/register?ref={user.referral_code}",
        "reward": float(settings.get_value(db, "referral.reward", 250)),
        "total_invited": len(refs),
        "verified": sum(1 for r in refs if r.status in ("verified", "rewarded")),
        "rewarded": sum(1 for r in refs if r.status == "rewarded"),
        "pending": sum(1 for r in refs if r.status == "pending"),
        "earnings": user.referral_cvx_earned or 0.0,
        "max_monthly": int(settings.get_value(db, "referral.max_monthly", 10)),
        "referrals_this_month": this_month,
    }


def rows(db: Session, user_id: str, page: int = 1, page_size: int = 20) -> tuple[list[Referral], int]:
    q = db.query(Referral).filter(Referral.referrer_id == user_id).order_by(Referral.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def settings_env():
    from app.core.config import settings

    return settings
