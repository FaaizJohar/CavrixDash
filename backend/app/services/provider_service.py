from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.crypto import encrypt_secret, mask_secret
from app.core.errors import AppError, NotFoundError
from app.core.logging import get_logger
from app.models.offer import Offer
from app.models.provider import Provider, ProviderCredential
from app.providers.registry import get_adapter

log = get_logger("provider")


def get_provider(db: Session, provider_id: str) -> Provider:
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise NotFoundError("Provider not found.")
    return p


def get_by_code(db: Session, code: str) -> Provider | None:
    return db.query(Provider).filter(Provider.code == code).first()


def list_providers(db: Session) -> list[Provider]:
    return db.query(Provider).order_by(Provider.priority.asc()).all()


def get_credentials(db: Session, provider_id: str) -> dict[str, str]:
    rows = (
        db.query(ProviderCredential)
        .filter(ProviderCredential.provider_id == provider_id)
        .all()
    )
    return {r.name: decrypt_cred(r) for r in rows}


def decrypt_cred(row: ProviderCredential) -> str:
    from app.core.crypto import decrypt_secret

    return decrypt_secret(row.value_encrypted) if row.value_encrypted else ""


def set_credentials(db: Session, provider: Provider, values: dict[str, str]) -> None:
    existing = {
        r.name: r for r in db.query(ProviderCredential).filter(ProviderCredential.provider_id == provider.id)
    }
    for name, value in values.items():
        if value is None:
            continue
        enc = encrypt_secret(value)
        masked = mask_secret(value)
        row = existing.get(name)
        if row:
            row.value_encrypted = enc
            row.masked = masked
            row.rotated_at = datetime.now(timezone.utc).isoformat()
        else:
            db.add(
                ProviderCredential(
                    provider_id=provider.id,
                    name=name,
                    value_encrypted=enc,
                    masked=masked,
                    rotated_at=datetime.now(timezone.utc).isoformat(),
                )
            )
    db.commit()


def masked_credentials(db: Session, provider_id: str) -> dict[str, str]:
    rows = db.query(ProviderCredential).filter(ProviderCredential.provider_id == provider_id).all()
    return {r.name: (r.masked or "••••••••") for r in rows}


def create_provider(db: Session, data: dict[str, Any]) -> Provider:
    if get_by_code(db, data["code"]):
        raise AppError("A provider with this code already exists.", code="PROVIDER_EXISTS")
    provider = Provider(
        code=data["code"],
        name=data["name"],
        kind=data.get("kind", "offerwall"),
        enabled=data.get("enabled", True),
        priority=data.get("priority", 0),
        reward_multiplier=data.get("reward_multiplier", 1.0),
        meta=json.dumps(data.get("meta", {}), ensure_ascii=False),
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    if data.get("credentials"):
        set_credentials(db, provider, data["credentials"])
    return provider


def update_provider(db: Session, provider: Provider, data: dict[str, Any]) -> Provider:
    for field in ("name", "kind", "enabled", "priority", "reward_multiplier", "reliability"):
        if field in data and data[field] is not None:
            setattr(provider, field, data[field])
    if data.get("meta") is not None:
        provider.meta = json.dumps(data["meta"], ensure_ascii=False)
    if data.get("credentials"):
        set_credentials(db, provider, data["credentials"])
    db.commit()
    db.refresh(provider)
    return provider


def test_connection(db: Session, provider: Provider) -> dict[str, Any]:
    adapter = get_adapter(provider.code)
    if not adapter:
        raise NotFoundError("No adapter registered for this provider.")
    creds = get_credentials(db, provider.id)
    try:
        result = adapter.test_connection(creds)
    except Exception as exc:
        result = {"ok": False, "message": str(exc)}
    provider.status = "connected" if result.get("ok") else "error"
    if not result.get("ok"):
        provider.last_error = str(result.get("message", ""))[:2000]
    db.commit()
    return result


def sync_offers(db: Session, provider: Provider) -> int:
    adapter = get_adapter(provider.code)
    if not adapter:
        raise NotFoundError("No adapter registered for this provider.")
    creds = get_credentials(db, provider.id)
    try:
        raw_offers = adapter.sync_offers(creds)
    except Exception as exc:
        provider.status = "error"
        provider.last_error = str(exc)[:2000]
        db.commit()
        raise AppError(f"Offer sync failed: {exc}", code="PROVIDER_SYNC_FAILED")

    existing = {
        o.external_id: o for o in db.query(Offer).filter(Offer.provider_id == provider.id)
    }
    now = datetime.now(timezone.utc).isoformat()
    created = updated = 0
    for raw in raw_offers:
        ext = raw["external_id"]
        row = existing.get(ext)
        if row:
            row.title = raw["title"]
            row.description = raw["description"]
            row.category = raw["category"]
            row.icon_url = raw["icon_url"]
            row.reward = raw["reward"]
            row.payout = raw["payout"]
            row.estimated_time = raw["estimated_time"]
            row.countries = json.dumps(raw["countries"])
            row.devices = json.dumps(raw["devices"])
            row.requirements = raw["requirements"]
            row.conversion_event = raw["conversion_event"]
            row.click_url = raw["click_url"]
            row.landing_url = raw.get("landing_url", "")
            row.status = raw.get("status", "active")
            row.meta = json.dumps(raw.get("meta", {}), ensure_ascii=False)
            updated += 1
        else:
            db.add(
                Offer(
                    provider_id=provider.id,
                    external_id=ext,
                    title=raw["title"],
                    description=raw["description"],
                    category=raw["category"],
                    icon_url=raw["icon_url"],
                    reward=raw["reward"],
                    payout=raw["payout"],
                    estimated_time=raw["estimated_time"],
                    countries=json.dumps(raw["countries"]),
                    devices=json.dumps(raw["devices"]),
                    requirements=raw["requirements"],
                    conversion_event=raw["conversion_event"],
                    click_url=raw["click_url"],
                    landing_url=raw.get("landing_url", ""),
                    status=raw.get("status", "active"),
                    meta=json.dumps(raw.get("meta", {}), ensure_ascii=False),
                )
            )
            created += 1
    provider.last_synced_at = now
    provider.status = "connected"
    provider.last_error = ""
    db.commit()
    return created + updated


def track_provider_revenue(db: Session, provider: Provider, amount: float) -> None:
    provider.revenue_tracked = round((provider.revenue_tracked or 0) + amount, 4)
    db.flush()


def _parse_dt(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_sync_due(db: Session, provider: Provider) -> bool:
    """Whether a background offer-sync should run for this provider.

    Healthy providers sync at most once per `provider_sync_interval_minutes`.
    After consecutive failures the delay grows exponentially:
    base * 2^(failures - 1), capped at `provider_sync_max_backoff_minutes`.
    """
    from app.core.config import settings as app_settings

    last = provider.last_attempt_at or provider.last_synced_at or ""
    if not last:
        return True
    last_dt = _parse_dt(last)
    if last_dt is None:
        return True
    elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
    failures = provider.sync_error_count or 0
    if failures:
        delay = app_settings.provider_sync_error_base_seconds * (2 ** min(failures - 1, 8))
        delay = min(delay, app_settings.provider_sync_max_backoff_minutes * 60)
    else:
        delay = app_settings.provider_sync_interval_minutes * 60
    return elapsed >= delay


def sync_enabled_providers(db: Session) -> dict[str, Any]:
    """Worker entry point: sync offers for every due, enabled provider.

    Applies exponential backoff on failures and resets the failure counter (and
    updates `last_synced_at`) on success. Never raises; per-provider errors are
    recorded on the row and returned in the summary.
    """
    providers = (
        db.query(Provider)
        .filter(Provider.enabled == True)  # noqa: E712
        .order_by(Provider.priority.asc())
        .all()
    )
    summary: dict[str, Any] = {
        "providers": len(providers),
        "synced": [],
        "pending_backoff": 0,
        "failed": [],
        "offers": 0,
    }
    if not providers:
        return summary

    now = datetime.now(timezone.utc).isoformat()
    for p in providers:
        if not is_sync_due(db, p):
            summary["pending_backoff"] += 1
            continue
        p.last_attempt_at = now
        try:
            count = sync_offers(db, p)
        except AppError as exc:
            p.status = "error"
            p.last_error = str(exc.message)[:2000]
            p.sync_error_count = (p.sync_error_count or 0) + 1
            db.commit()
            summary["failed"].append({"code": p.code, "message": str(exc.message)})
            log.warning("provider_sync_failed", provider=p.code, attempt=p.sync_error_count)
            continue
        except Exception as exc:  # pragma: no cover
            p.status = "error"
            p.last_error = repr(exc)[:2000]
            p.sync_error_count = (p.sync_error_count or 0) + 1
            db.commit()
            summary["failed"].append({"code": p.code, "message": repr(exc)})
            log.warning("provider_sync_failed", provider=p.code, attempt=p.sync_error_count)
            continue
        p.sync_error_count = 0
        db.commit()
        summary["synced"].append(p.code)
        summary["offers"] += int(count)
        log.info("provider_synced", provider=p.code, offers=int(count))

    return summary
