from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.offer import Offer
from app.models.provider import Provider
from app.models.tracking import TaskClick
from app.models.user import User
from app.providers.registry import get_adapter
from app.services import provider_service, settings_service as settings


def _country_match(countries: list[str], country: str) -> bool:
    if not countries:
        return True
    if not country:
        return True
    return "ALL" in countries or country.upper() in [c.upper() for c in countries]


def _device_match(devices: list[str], device: str) -> bool:
    if not devices:
        return True
    if not device:
        return True
    return device in devices


def list_offers(
    db: Session,
    *,
    category: str | None = None,
    sort: str = "recommended",
    device: str | None = None,
    country: str | None = None,
    page: int = 1,
    page_size: int = 24,
) -> tuple[list[Offer], int]:
    now = datetime.now(timezone.utc).isoformat()
    q = db.query(Offer).join(Provider, Provider.id == Offer.provider_id).filter(
        Offer.status == "active",
        Provider.enabled == True,  # noqa: E712
        or_(Offer.expires_at == "", Offer.expires_at == "0", Offer.expires_at > now),
    )
    if category and category != "all":
        q = q.filter(Offer.category == category)
    offers = q.all()

    # Post-query filter for GEO/device because they are JSON columns.
    filtered = [
        o
        for o in offers
        if _country_match(json.loads(o.countries or "[]"), country or "")
        and _device_match(json.loads(o.devices or "[]"), device or "")
    ]

    if sort == "reward":
        filtered.sort(key=lambda o: o.effective_reward, reverse=True)
    elif sort == "fastest":
        filtered.sort(key=lambda o: o.estimated_time)
    elif sort == "conversion":
        filtered.sort(key=lambda o: o.conversion_rate, reverse=True)
    elif sort == "reliable":
        filtered.sort(key=lambda o: o.approval_rate, reverse=True)
    elif sort == "new":
        filtered.sort(key=lambda o: o.created_at, reverse=True)
    else:  # recommended (ranked)
        filtered.sort(key=_score_offer, reverse=True)

    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start : start + page_size]
    return items, total


def _score_offer(o: Offer) -> float:
    weights = _ranking_weights()
    payout = o.payout or o.reward / 1000.0
    conv = o.conversion_rate or 0.5
    appr = o.approval_rate or 0.9
    rel = 1.0
    provider = _provider_cache.get(o.provider_id)
    if provider:
        rel = provider.reliability or 1.0
    featured = 0.5 if o.featured else 0.0
    score = (
        payout * weights["payout"]
        + conv * weights["conversion"]
        + appr * weights["approval"]
        + rel * weights["reliability"]
    )
    return score + featured


_provider_cache: dict[str, Provider] = {}


def set_provider_cache(cache: dict[str, Provider]) -> None:
    global _provider_cache
    _provider_cache = cache


def _ranking_weights() -> dict[str, float]:
    import os

    # Live weights come from global config via settings_service; read lazily.
    try:
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            w = settings.load_config(db).get("ranking", {})
            return {
                "payout": float(w.get("payout_weight", 0.4)),
                "conversion": float(w.get("conversion_weight", 0.25)),
                "approval": float(w.get("approval_weight", 0.2)),
                "reliability": float(w.get("reliability_weight", 0.15)),
            }
        finally:
            db.close()
    except Exception:
        return {"payout": 0.4, "conversion": 0.25, "approval": 0.2, "reliability": 0.15}


def get_offer(db: Session, offer_id: str) -> Offer:
    o = db.query(Offer).filter(Offer.id == offer_id).first()
    if not o:
        raise NotFoundError("Offer not found.")
    return o


def create_click(
    db: Session,
    user: User,
    offer: Offer,
    *,
    ip: str,
    user_agent: str,
    device_id: str,
) -> TaskClick:
    if not settings.get_value(db, "tasks.offers_enabled", True):
        raise AppError("Earning is currently disabled.", code="EARNING_DISABLED")

    provider = provider_service.get_provider(db, offer.provider_id)
    adapter = get_adapter(provider.code)
    if not adapter:
        raise AppError("Provider adapter unavailable.", code="PROVIDER_UNAVAILABLE")
    if not provider.enabled:
        raise AppError("This offer's provider is offline.", code="PROVIDER_OFFLINE")

    # per-user offer limit
    user_completions = (
        db.query(TaskClick)
        .filter(TaskClick.user_id == user.id, TaskClick.offer_id == offer.id)
        .count()
    )
    if offer.per_user_limit and user_completions >= offer.per_user_limit:
        raise AppError("You've already completed this task.", code="OFFER_LIMIT")

    # daily cap across users
    if offer.daily_cap:
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=24)
        today_count = (
            db.query(TaskClick)
            .filter(TaskClick.offer_id == offer.id, TaskClick.created_at >= since)
            .count()
        )
        if today_count >= offer.daily_cap:
            raise AppError("This offer reached its daily limit.", code="OFFER_DAILY_CAP")

    click = TaskClick(
        click_id=secrets.token_hex(16),
        user_id=user.id,
        offer_id=offer.id,
        provider_id=provider.id,
        session_id=secrets.token_hex(8),
        ip=ip,
        user_agent=user_agent[:2000],
        device_id=device_id or f"dev-{secrets.token_hex(8)}",
        reward_offered=offer.effective_reward,
        country=(ip or ""),
        meta=json.dumps({"token": secrets.token_urlsafe(16)}, ensure_ascii=False),
    )
    db.add(click)
    db.flush()

    token = json.loads(click.meta)["token"]
    click_ctx = {"click_id": click.click_id, "token": token}
    try:
        redirect_url = adapter.build_click_url(offer.__dict__, click_ctx, provider_service.get_credentials(db, provider.id))
    except Exception:
        redirect_url = offer.landing_url or offer.click_url
    click.redirect_url = redirect_url
    db.commit()
    db.refresh(click)
    return click


def list_my_tasks(db: Session, user_id: str, page: int = 1, page_size: int = 20) -> tuple[list[TaskClick], int]:
    q = (
        db.query(TaskClick)
        .filter(TaskClick.user_id == user_id)
        .order_by(TaskClick.created_at.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_click(db: Session, click_id: str) -> TaskClick | None:
    return db.query(TaskClick).filter(TaskClick.click_id == click_id).first()
