from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.core.errors import AppError
from app.models.cvx import Campaign
from app.models.notification import Notification
from app.models.offer import Offer
from app.models.tracking import Conversion, Postback, Reversal, TaskClick
from app.models.user import User
from app.providers.registry import get_adapter
from app.services import cvx_service, fraud_service, notification_service, provider_service
from app.services import settings_service as settings
from app.services.task_service import get_click


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def active_campaign_bonus(db: Session) -> tuple[float, float]:
    """Returns (multiplier, flat_bonus) from active campaigns."""
    now = datetime.now(timezone.utc).isoformat()
    multiplier = 1.0
    bonus = 0.0
    campaigns = (
        db.query(Campaign)
        .filter(Campaign.enabled == True)  # noqa: E712
        .all()
    )
    for c in campaigns:
        if c.starts_at and c.starts_at > now:
            continue
        if c.ends_at and c.ends_at < now:
            continue
        if c.kind == "multiplier" and c.applies_to in ("all", "offerwall"):
            multiplier = max(multiplier, c.multiplier)
        elif c.kind == "bonus" and c.applies_to in ("all", "offerwall"):
            bonus += c.multiplier
    return multiplier, bonus


def compute_reward(db: Session, offer: Offer, provider) -> float:
    global_multiplier = float(settings.get_value(db, "cvx.global_multiplier", 1.0))
    campaign_mult, bonus = active_campaign_bonus(db)
    reward = (
        offer.reward
        * provider.reward_multiplier
        * offer.multiplier
        * global_multiplier
        * campaign_mult
    )
    return round(reward + bonus, 2)


def handle_postback(
    db: Session,
    provider_code: str,
    payload: dict[str, Any],
    raw_body: str,
    ip: str,
) -> dict[str, Any]:
    provider = provider_service.get_by_code(db, provider_code)
    if not provider or not provider.enabled:
        # Always ack unknown/disabled providers to prevent retry storms.
        _store_postback(db, provider_code, {}, False, ip, "unknown_provider")
        return {"status": "ignored", "message": "Provider not recognized"}

    adapter = get_adapter(provider.code)
    if not adapter:
        _store_postback(db, provider.id, json.dumps(payload), False, ip, "no_adapter")
        return {"status": "ignored", "message": "No adapter"}

    try:
        normalized = adapter.parse_postback(payload, provider_service.get_credentials(db, provider.id), raw_body)
    except AppError as exc:
        _store_postback(db, provider.id, json.dumps(payload), False, ip, f"invalid:{exc.code}")
        return {"status": "invalid", "message": exc.message, "code": exc.code}

    # Replay / idempotency guard — unique on (provider, conversion_id)
    existing = (
        db.query(Conversion)
        .filter(
            Conversion.provider_id == provider.id,
            Conversion.conversion_id == normalized["conversion_id"],
        )
        .first()
    )
    if existing:
        _store_postback(
            db, provider.id, json.dumps(payload), normalized["signature_valid"], ip,
            f"duplicate:conversion:{existing.status}",
        )
        return {"status": "duplicate", "conversion_status": existing.status}

    click = get_click(db, normalized["click_id"])
    if not click:
        _store_postback(db, provider.id, json.dumps(payload), normalized["signature_valid"], ip, "click_not_found")
        return {"status": "ignored", "message": "Click not found"}

    if click.user_id:
        user = db.query(User).filter(User.id == click.user_id).first()
    else:
        user = None

    postback = _store_postback(db, provider.id, json.dumps(payload), normalized["signature_valid"], ip, "processing")

    conversion = Conversion(
        click_id=click.click_id,
        user_id=click.user_id,
        offer_id=click.offer_id,
        provider_id=provider.id,
        conversion_id=normalized["conversion_id"],
        external_tx_id=normalized.get("external_tx_id", ""),
        ip=ip,
        device_id=click.device_id,
        payout_amount=normalized.get("payout", 0),
        meta=json.dumps({"postback_id": postback.id}, ensure_ascii=False),
    )
    db.add(conversion)
    try:
        db.flush()
    except IntegrityError:
        # Replay raced with another request (or hit the DB-level unique
        # guard before the SELECT above saw it). Roll back the partial
        # write and record the duplicate instead of returning a 500.
        db.rollback()
        existing = (
            db.query(Conversion)
            .filter(
                Conversion.provider_id == provider.id,
                Conversion.conversion_id == normalized["conversion_id"],
            )
            .first()
        )
        _store_postback(
            db, provider.id, json.dumps(payload), normalized["signature_valid"], ip,
            f"duplicate:conversion:{existing.status if existing else 'unknown'}",
        )
        db.commit()
        return {
            "status": "duplicate",
            "conversion_status": existing.status if existing else "unknown",
        }

    status = normalized["status"]

    if status == "reversed":
        return _process_reversal(db, conversion, click, provider, normalized, user)

    if status == "rejected":
        conversion.status = "rejected"
        click.status = "rejected"
        if user:
            fraud_service.record_event(
                db,
                event_type="conversion_rejected",
                user_id=user.id,
                related_id=conversion.id,
                severity="low",
                ip=ip,
                description=normalized.get("reason", "Rejected by provider"),
            )
        db.commit()
        return {"status": "rejected", "conversion_id": conversion.id}

    # approved / held
    risk = fraud_service.evaluate_conversion_risk(
        db,
        user=user,
        click=click,
        conversion_id=conversion.conversion_id,
        device_id=click.device_id,
        ip=ip,
        exclude_id=conversion.id,
    )
    conversion.risk_score = risk["score"]
    click.risk_score = risk["score"]

    if risk["action"] == "reject":
        conversion.status = "rejected"
        click.status = "rejected"
        _fraud_record(db, user, conversion, ip, "auto_reject", risk, click.device_id)
        db.commit()
        return {"status": "rejected", "risk_score": risk["score"], "signals": risk["signals"]}

    if risk["action"] == "ban":
        conversion.status = "rejected"
        click.status = "rejected"
        if user:
            user.status = "suspended"
        _fraud_record(db, user, conversion, ip, "auto_ban", risk, click.device_id)
        db.commit()
        return {"status": "rejected", "risk_score": risk["score"], "signals": risk["signals"]}

    if risk["action"] == "hold":
        conversion.status = "held"
        click.status = "held"
        _fraud_record(db, user, conversion, ip, "auto_hold", risk, click.device_id)
        db.commit()
        return {"status": "held", "risk_score": risk["score"], "signals": risk["signals"]}

    # ---- approve ----
    offer = db.query(Offer).filter(Offer.id == click.offer_id).first()
    reward = compute_reward(db, offer, provider) if offer else click.reward_offered
    conversion.status = "approved"
    conversion.reward_amount = reward
    click.status = "approved"
    click.external_tx_id = normalized.get("external_tx_id", "")

    if user:
        try:
            cvx_service.credit(
                db,
                user,
                reward,
                "CREDIT",
                f"Task reward — {offer.title if offer else 'Offer'}",
                reference_type="conversion",
                reference_id=conversion.id,
                meta={"provider": provider.code, "offer_id": click.offer_id},
                created_by="system",
            )
        except AppError as exc:
            conversion.status = "held"
            click.status = "held"
            db.commit()
            return {"status": "held", "reason": exc.message}

        user.conversions_approved += 1
        user.tasks_completed += 1
        offer.completion_count += 1
        offer.revenue_earned = round((offer.revenue_earned or 0) + conversion.payout_amount, 4)
        provider_service.track_provider_revenue(db, provider, conversion.payout_amount)

        from app.services import referral_service

        referral_service.on_invitee_verified(db, user)

        notification_service.push(
            db,
            user.id,
            "conversion_approved",
            "Reward approved",
            f"{reward:,.0f} CVX has been credited to your wallet.",
            link="/rewards",
        )
        db.commit()
        return {
            "status": "approved",
            "conversion_id": conversion.id,
            "reward": reward,
            "risk_score": risk["score"],
        }

    db.commit()
    return {"status": "approved", "conversion_id": conversion.id}


def _process_reversal(
    db: Session, conversion: Conversion, click: TaskClick, provider, normalized: dict, user: User | None
) -> dict[str, Any]:
    conversion.status = "reversed"
    click.status = "reversed"
    reversal = Reversal(
        conversion_id=conversion.id,
        provider_id=provider.id,
        reason=normalized.get("reason", "Provider reversal"),
        raw_payload="",
        reversed_by="provider",
    )
    db.add(reversal)
    db.flush()
    reversal.raw_payload = f"{{conversion_id:{conversion.id}}}"

    if user:
        from app.services import cvx_service

        try:
            cvx_service.reversal(
                db,
                user,
                conversion.reward_amount,
                "Reward reversed by provider",
                reference_type="conversion",
                reference_id=conversion.id,
                meta={"provider": provider.code},
            )
            user.conversions_approved = max(0, (user.conversions_approved or 1) - 1)
            reversal.credited_back = "credited"
            notification_service.push(
                db,
                user.id,
                "conversion_reversed",
                "Reward reversed",
                "A provider reversed a conversion. Any CVX issued for it has been recovered.",
                link="/earn/my-tasks",
            )
        except AppError:
            reversal.credited_back = "failed"

    provider_service.track_provider_revenue(db, provider, -conversion.payout_amount)
    db.commit()
    return {"status": "reversed", "conversion_id": conversion.id}


def _fraud_record(db: Session, user: User | None, conversion: Conversion, ip: str, action: str, risk: dict, device_id: str) -> None:
    fraud_service.record_event(
        db,
        event_type="conversion_risk",
        user_id=user.id if user else "",
        related_id=conversion.id,
        severity=fraud_service.label(risk["score"]).lower(),
        score_delta=risk["score"],
        ip=ip,
        device_id=device_id,
        description="Auto decision: " + action + " | " + ", ".join(risk["signals"]),
        action=action,
    )


def _store_postback(
    db: Session,
    provider_id: str,
    raw: str,
    signature_valid: bool,
    ip: str,
    result: str,
) -> Postback:
    pb = Postback(
        provider_id=provider_id,
        raw_payload=raw[:10000],
        signature_valid="valid" if signature_valid else "invalid",
        nonce="",
        received_at=_now(),
        processed="pending",
        result=result[:2000],
        source_ip=ip,
    )
    db.add(pb)
    db.flush()
    return pb
