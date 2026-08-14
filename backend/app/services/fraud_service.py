from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.models.fraud import FraudEvent, FraudRule
from app.models.tracking import Conversion, TaskClick
from app.models.user import User
from app.services import settings_service as settings


def get_rule(db: Session, key: str, default: Any = None) -> Any:
    row = db.query(FraudRule).filter(FraudRule.key == key).first()
    if row and row.enabled == "true":
        try:
            return json.loads(row.value) if row.value.startswith(("{", "[")) else row.value
        except Exception:
            return row.value
    return settings.get_value(db, f"fraud.{key}", default)


def record_event(
    db: Session,
    *,
    event_type: str,
    user_id: str = "",
    related_id: str = "",
    severity: str = "medium",
    score_delta: float = 0.0,
    ip: str = "",
    device_id: str = "",
    description: str = "",
    action: str = "",
    meta: dict[str, Any] | None = None,
) -> FraudEvent:
    ev = FraudEvent(
        event_type=event_type,
        user_id=user_id,
        related_id=related_id,
        severity=severity,
        score_delta=score_delta,
        ip=ip,
        device_id=device_id,
        description=description[:1000],
        action=action,
        meta=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(ev)
    db.flush()
    return ev


def _clamp(score: float) -> float:
    return max(0.0, min(100.0, score))


def check_duplicate_conversion(db: Session, conversion_id: str, exclude_id: str | None = None) -> bool:
    q = db.query(Conversion).filter(
        Conversion.conversion_id == conversion_id, Conversion.status != "rejected"
    )
    if exclude_id:
        q = q.filter(Conversion.id != exclude_id)
    return q.first() is not None


def check_click_reuse(db: Session, click_id: str) -> bool:
    existing = (
        db.query(Conversion)
        .filter(Conversion.click_id == click_id, Conversion.status != "rejected")
        .first()
    )
    return existing is not None


def evaluate_conversion_risk(
    db: Session,
    *,
    user: User,
    click: TaskClick,
    conversion_id: str,
    device_id: str,
    ip: str,
    exclude_id: str | None = None,
) -> dict[str, Any]:
    """Returns {score, signals: [...], action}."""
    score = 0.0
    signals: list[str] = []
    penalties: dict[str, float] = {}

    # 1. duplicate conversion id / click reuse
    if check_duplicate_conversion(db, conversion_id, exclude_id=exclude_id):
        signals.append("duplicate_conversion_id")
        penalties["duplicate_conversion_id"] = 90
        score += 90

    if check_click_reuse(db, click.id):
        signals.append("repeated_click")
        penalties["repeated_click"] = 40
        score += 40

    # 2. impossible completion time
    min_seconds = int(get_rule(db, "impossible_completion_seconds", 45))
    created = click.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - created).total_seconds()
    if elapsed < min_seconds:
        signals.append("impossible_completion_time")
        penalties["impossible_completion_time"] = 25
        score += 25

    # 3. same device conversions
    dev_limit = int(get_rule(db, "same_device_conversion_limit", 3))
    dev_count = (
        db.query(func.count(Conversion.id))
        .filter(
            Conversion.user_id == user.id,
            Conversion.device_id == device_id,
            Conversion.status != "rejected",
        )
        .scalar()
    )
    if device_id and dev_count >= dev_limit:
        signals.append("same_device_limit")
        penalties["same_device_limit"] = 30
        score += 30

    # 4. duplicate IP conversions
    ip_limit = int(get_rule(db, "duplicate_ip_conversion_limit", 5))
    ip_count = (
        db.query(func.count(Conversion.id))
        .filter(Conversion.ip == ip, Conversion.status != "rejected")
        .scalar()
    )
    if ip and ip_count >= ip_limit:
        signals.append("shared_ip_limit")
        penalties["shared_ip_limit"] = 20
        score += 20

    # 5. task velocity (redis)
    hour_window = int(get_rule(db, "max_task_velocity_per_hour", 12))
    v = rate_limit.incr(f"velocity:{user.id}:{int(datetime.now(timezone.utc).timestamp()) // 3600}", 3600)
    if v > hour_window:
        signals.append("task_velocity")
        penalties["task_velocity"] = 15
        score += 15

    # 6. VPN/proxy signal hook (placeholder — extend with real IP-intel provider)
    if _is_proxy_ip(ip):
        signals.append("proxy_ip")
        penalties["proxy_ip"] = int(get_rule(db, "vpn_proxy_penalty", 25))
        score += penalties["proxy_ip"]

    # 7. multi-account farming (same device under several users)
    if device_id:
        users_on_device = (
            db.query(func.count(func.distinct(Conversion.user_id)))
            .filter(Conversion.device_id == device_id, Conversion.status != "rejected")
            .scalar()
        )
        if users_on_device >= int(get_rule(db, "max_devices_per_user", 4)):
            signals.append("device_farming")
            penalties["device_farming"] = 35
            score += 35

    score = _clamp(score)
    action = "allow"
    if score >= float(get_rule(db, "auto_ban_score", 95)):
        action = "ban"
    elif score >= float(get_rule(db, "auto_reject_score", 80)):
        action = "reject"
    elif score >= float(get_rule(db, "auto_hold_score", 60)):
        action = "hold"

    return {"score": round(score, 1), "signals": signals, "action": action}


def _is_proxy_ip(ip: str) -> bool:
    """Integration point for IP intelligence (e.g. IPQualityScore / ipinfo).
    Returns False by default. Wire real checks behind a flag."""
    if not ip:
        return False
    if rate_limit.get(f"proxy:{ip}"):
        return rate_limit.get(f"proxy:{ip}") == "1"
    return False


def check_login_risk(db: Session, user: User, ip: str) -> bool:
    if not ip or not user.last_login_ip:
        return False
    if user.last_login_ip == ip:
        return False
    recent = db.query(FraudEvent).filter(
        FraudEvent.user_id == user.id,
        FraudEvent.event_type.in_(["suspicious_login", "login_blocked"]),
        FraudEvent.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
    ).count()
    if recent >= 3:
        record_event(
            db,
            event_type="login_blocked",
            user_id=user.id,
            severity="high",
            score_delta=10,
            ip=ip,
            description=f"Login blocked from new IP {ip} (3+ risk events in 24h)",
        )
        db.commit()
        return True
    return False


def record_login_anomaly(db: Session, user: User, ip: str) -> None:
    if user.last_login_ip and user.last_login_ip != ip:
        record_event(
            db,
            event_type="suspicious_login",
            user_id=user.id,
            severity="medium",
            score_delta=5,
            ip=ip,
            description=f"Login from different IP ({user.last_login_ip} -> {ip})",
        )
        db.commit()


def label(score: float) -> str:
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    if score <= 80:
        return "High"
    return "Critical"
