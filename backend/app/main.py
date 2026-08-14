from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    admin,
    analytics,
    auth,
    conversions,
    cvx,
    health,
    notifications,
    offers,
    postbacks,
    referrals,
    servers,
    support,
    tasks,
    users,
    ws,
)
from app.core import errors
from app.core.config import settings
from app.core.database import check_db_ready, init_db
from app.core.logging import get_logger, setup_logging
from app.core.middleware import SecurityHeadersMiddleware

setup_logging()
log = get_logger("main")

app = FastAPI(
    title="Cavrix Cloud API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware, is_prod=True)

errors.register_error_handlers(app)

API = settings.api_v1_prefix

app.include_router(auth.router, prefix=API)
app.include_router(users.router, prefix=API)
app.include_router(offers.router, prefix=API)
app.include_router(tasks.router, prefix=API)
app.include_router(conversions.router, prefix=API)
app.include_router(postbacks.router, prefix=API)
app.include_router(cvx.router, prefix=API)
app.include_router(servers.router, prefix=API)
app.include_router(referrals.router, prefix=API)
app.include_router(analytics.router, prefix=API)
app.include_router(support.router, prefix=API)
app.include_router(notifications.router, prefix=API)
app.include_router(health.router, prefix=API)

for mod in (admin.overview, admin.users, admin.infrastructure, admin.economy, admin.platform, admin.config):
    app.include_router(mod.router, prefix=API)

app.include_router(ws.router)


@app.get("/healthz", tags=["health"])
def healthz():
    db_ok = check_db_ready()
    return {"ok": db_ok, "app": settings.app_name, "env": settings.app_env}


@app.on_event("startup")
def on_startup() -> None:
    if settings.app_env.lower() != "test":
        try:
            if settings.db_auto_create and not settings.is_prod:
                # Dev uses create_all; production schema comes from Alembic
                # (run via the migrate service before the API starts).
                init_db()
            from app.services.seed import ensure_bootstrap

            ensure_bootstrap()
            log.info("startup_ready", db="auto")
        except Exception as exc:
            log.error("startup_failed", exc=repr(exc))
    log.info("api_started", env=settings.app_env)
