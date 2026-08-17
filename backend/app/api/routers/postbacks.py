from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_client_meta
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.core.rate_limit import get, hit, set_ttl
from app.services import conversion_service, provider_service

router = APIRouter(prefix="/postbacks", tags=["postbacks"])
log = get_logger("postbacks")

_STATUS_MAP = {
    "reward": "approved",
    "install": "approved",
    "approved": "approved",
    "complete": "approved",
    "rejected": "rejected",
    "reversal": "reversed",
    "reversed": "reversed",
    "chargeback": "reversed",
    "held": "held",
    "pending": "held",
}


@router.post("/adgem")
async def adgem_postback(request: Request, db: Session = Depends(get_db)):
    hit("postback", "ad_gem", settings.rate_limit_postback_per_min)

    raw = (await request.body()).decode("utf-8", errors="replace")

    secret = settings.adgem_postback_key
    if not secret:
        log.error("adgem_postback_key_not_configured")
        return Response(status_code=500, content=json.dumps(
            {"status": "error", "message": "Postback key not configured"}
        ), media_type="application/json")

    sig = request.headers.get("Signature", "")
    if not sig:
        return Response(status_code=401, content=json.dumps(
            {"status": "error", "message": "Missing Signature header"}
        ), media_type="application/json")

    expected = hmac_mod.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac_mod.compare_digest(expected, sig):
        _store_event(db, "ad_gem", "postback_rejected", raw,
                     "invalid_signature", get_client_meta(request)["ip"])
        return Response(status_code=401, content=json.dumps(
            {"status": "error", "message": "Invalid signature"}
        ), media_type="application/json")

    try:
        payload = json.loads(raw) if raw else {}
    except Exception:
        return Response(status_code=422, content=json.dumps(
            {"status": "error", "message": "Invalid JSON"}
        ), media_type="application/json")

    if not isinstance(payload, dict):
        return Response(status_code=422, content=json.dumps(
            {"status": "error", "message": "Expected JSON object"}
        ), media_type="application/json")

    ts = payload.get("timestamp", 0)
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        ts = 0
    if ts and abs(time.time() - ts) > 300:
        return Response(status_code=422, content=json.dumps(
            {"status": "error", "message": "Timestamp expired (±5 min)"}
        ), media_type="application/json")

    request_id = payload.get("request_id", "")
    if request_id:
        rk = f"adgem:rid:{request_id}"
        if get(rk):
            _store_event(db, "ad_gem", "postback_duplicate", raw,
                         f"replay:{request_id}", get_client_meta(request)["ip"])
            return {"status": "duplicate", "message": "Request already processed"}
        set_ttl(rk, "1", 86400)

    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    conversion_id = str(data.get("conversion_id") or "")
    if not conversion_id:
        return Response(status_code=422, content=json.dumps(
            {"status": "error", "message": "Missing data.conversion_id"}
        ), media_type="application/json")

    click_id = str(data.get("sub_id") or payload.get("sub_id") or "")
    player_id = str(data.get("player_id") or "")
    payout = float(data.get("payout") or 0)
    status_raw = str(
        data.get("conversion_type")
        or data.get("event")
        or payload.get("status")
        or "reward"
    ).lower()
    status = _STATUS_MAP.get(status_raw, "approved")

    if not click_id and player_id:
        from app.models.user import User
        from app.models.tracking import TaskClick

        user = db.query(User).filter(User.username == player_id).first()
        if user:
            click = (
                db.query(TaskClick)
                .filter(
                    TaskClick.user_id == user.id,
                    TaskClick.status.in_(["pending", "held"]),
                )
                .order_by(TaskClick.created_at.desc())
                .first()
            )
            if click:
                click_id = click.click_id

    if not click_id:
        log.warning("adgem_click_not_found", player_id=player_id, conversion_id=conversion_id)

    normalized = {
        "click_id": click_id,
        "conversion_id": conversion_id,
        "external_tx_id": conversion_id,
        "payout": payout,
        "status": status,
        "reason": str(data.get("reason") or payload.get("reason") or ""),
        "signature_valid": True,
    }

    meta = get_client_meta(request)
    _store_event(db, "ad_gem", "postback_received", raw, "processing", meta["ip"])

    result = conversion_service.handle_postback(
        db, "ad_gem", payload, raw, meta["ip"], pre_normalized=normalized
    )
    return result


@router.post("/{provider_code}")
async def postback(provider_code: str, request: Request, db: Session = Depends(get_db)):
    hit("postback", provider_code, settings.rate_limit_postback_per_min)
    raw = (await request.body()).decode("utf-8", errors="replace")
    try:
        payload = await request.json()
    except Exception:
        try:
            payload = json.loads(raw or "{}")
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        payload = {"raw": raw}
    meta = get_client_meta(request)
    result = conversion_service.handle_postback(
        db, provider_code, payload, raw, meta["ip"]
    )
    return result


def _store_event(
    db: Session,
    provider_code: str,
    event_type: str,
    raw_payload: str,
    result: str,
    ip: str,
) -> None:
    from app.models.provider import ProviderEvent

    provider = provider_service.get_by_code(db, provider_code)
    provider_id = provider.id if provider else ""
    ev = ProviderEvent(
        provider_id=provider_id,
        event_type=event_type,
        raw_payload=raw_payload[:10000],
        status="processed" if "received" in event_type else "rejected",
        result=result[:2000],
        source_ip=ip,
    )
    db.add(ev)
    db.flush()
