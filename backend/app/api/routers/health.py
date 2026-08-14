from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.core.database import check_db_ready

router = APIRouter(tags=["health"])

APP_VERSION = "1.0.0"


@router.get("/health", response_model=dict)
def health() -> dict:
    db_ok = check_db_ready()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "down",
        "app": settings.app_name,
        "env": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready", response_model=dict)
def ready() -> dict:
    db_ok = check_db_ready()
    return {
        "ready": db_ok,
        "database": "ok" if db_ok else "down",
        "env": settings.app_env,
    }


@router.get("/version", response_model=dict)
def version() -> dict:
    return {
        "version": APP_VERSION,
        "name": settings.app_name,
        "env": settings.app_env,
    }
