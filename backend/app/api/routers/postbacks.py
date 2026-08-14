from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_client_meta
from app.core.errors import NotFoundError
from app.core.rate_limit import hit
from app.services import conversion_service, provider_service

router = APIRouter(prefix="/postbacks", tags=["postbacks"])


@router.post("/{provider_code}")
async def postback(provider_code: str, request: Request, db: Session = Depends(get_db)):
    hit("postback", provider_code, settings.rate_limit_postback_per_min)
    raw = (await request.body()).decode("utf-8", errors="replace")
    try:
        payload = await request.json()
    except Exception:
        import json

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
