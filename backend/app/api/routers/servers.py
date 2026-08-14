from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError, NotFoundError
from app.core.config import settings as app_settings
from app.core.rate_limit import hit as rate_hit
from app.models.user import User
from app.schemas import server as s
from app.schemas.common import Paginated
from app.services import server_service, settings_service as settings
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("/plans", response_model=list[s.PlanOut])
def plans(db: Session = Depends(get_db)):
    return [s.PlanOut.model_validate(p, from_attributes=True) for p in server_service.list_plans(db)]


@router.get("/regions", response_model=list[s.RegionOut])
def regions(db: Session = Depends(get_db)):
    return [s.RegionOut.model_validate(r, from_attributes=True) for r in server_service.list_regions(db)]


@router.get("/templates", response_model=list[s.TemplateOut])
def templates(db: Session = Depends(get_db)):
    return [s.TemplateOut.model_validate(t, from_attributes=True) for t in server_service.list_templates(db)]


@router.get("/upgrades/prices", response_model=list[s.UpgradePriceOut])
def upgrade_prices(db: Session = Depends(get_db)):
    return [s.UpgradePriceOut.model_validate(p, from_attributes=True) for p in server_service.list_upgrade_prices(db)]


@router.get("", response_model=list[s.ServerOut])
def my_servers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    servers = server_service.my_servers(db, user.id)
    return server_service.serialize(db, servers)


@router.post("", response_model=s.ServerOut)
def claim(payload: s.CreateServerRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rate_hit("server_create", user.id, app_settings.rate_limit_server_create_per_min)
    server = server_service.claim_server(
        db,
        user,
        plan_id=payload.plan_id,
        region=payload.region,
        template_id=payload.template_id,
        version=payload.version,
        server_name=payload.server_name,
        ip=request.client.host if request.client else "",
    )
    return server_service.serialize(db, server)


@router.get("/{server_id}", response_model=s.ServerOut)
def detail(server_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = server_service.get_server(db, user, server_id)
    return server_service.serialize(db, server)


@router.post("/{server_id}/action", response_model=dict)
def action(server_id: str, payload: s.ServerActionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rate_hit("server_action", user.id, app_settings.rate_limit_server_action_per_min)
    server = server_service.get_server(db, user, server_id)
    return server_service.server_action(db, user, server, payload.action)


@router.get("/{server_id}/stats", response_model=dict)
def stats(server_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = server_service.get_server(db, user, server_id)
    return server_service.fetch_resources(db, server)


@router.get("/{server_id}/files", response_model=list)
def files(server_id: str, path: str = "/", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = server_service.get_server(db, user, server_id)
    return server_service.list_files(db, server, path)


@router.get("/{server_id}/backups", response_model=list)
def backups(server_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = server_service.get_server(db, user, server_id)
    return server_service.list_backups(db, server)


@router.post("/{server_id}/backups/{backup_id}/restore", response_model=dict)
def restore(server_id: str, backup_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = server_service.get_server(db, user, server_id)
    server_service.restore_backup(db, server, backup_id)
    return {"ok": True}


@router.get("/{server_id}/schedules", response_model=list)
def schedules(server_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = server_service.get_server(db, user, server_id)
    return server_service.list_schedules(db, server)


@router.get("/{server_id}/network", response_model=list)
def network(server_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = server_service.get_server(db, user, server_id)
    return server_service.list_network(db, server)


@router.post("/{server_id}/upgrades/preview", response_model=s.UpgradeQuote)
def upgrade_preview(server_id: str, payload: s.UpgradePurchaseRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = server_service.get_server(db, user, server_id)
    return server_service.quote_upgrade(db, server, payload.upgrade_type, payload.amount)


@router.post("/{server_id}/upgrades", response_model=s.UpgradeOut)
def buy_upgrade(server_id: str, payload: s.UpgradePurchaseRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rate_hit("server_action", user.id, app_settings.rate_limit_server_action_per_min)
    server = server_service.get_server(db, user, server_id)
    up = server_service.buy_upgrade(db, user, server, payload.upgrade_type, payload.amount)
    return s.UpgradeOut.model_validate(up, from_attributes=True)


@router.post("/{server_id}/renew", response_model=s.ServerOut)
def renew(server_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rate_hit("server_action", user.id, app_settings.rate_limit_server_action_per_min)
    server = server_service.get_server(db, user, server_id)
    server = server_service.renew_server(db, user, server)
    return server_service.serialize(db, server)
