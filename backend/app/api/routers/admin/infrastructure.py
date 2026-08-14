from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_infra
from app.core.errors import NotFoundError
from app.models.server import PterodactylNode, Region, ServerPlan, ServerTemplate, UpgradePrice
from app.schemas import admin as s
from app.schemas import server as ss
from app.schemas.common import Paginated
from app.api.deps import build_page, page_params

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/plans", response_model=Paginated[ss.PlanOut], dependencies=[Depends(require_infra)])
def plans(_page: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)):
    page, page_size = _page
    q = db.query(ServerPlan).order_by(ServerPlan.sort_order.asc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return build_page([ss.PlanOut.model_validate(p, from_attributes=True) for p in items], total, page, page_size)


@router.patch("/plans/{plan_id}", response_model=ss.PlanOut, dependencies=[Depends(require_infra)])
def update_plan(plan_id: str, payload: s.PlanUpdate, db: Session = Depends(get_db)):
    p = db.query(ServerPlan).filter(ServerPlan.id == plan_id).first()
    if not p:
        raise NotFoundError("Plan not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return ss.PlanOut.model_validate(p, from_attributes=True)


@router.get("/regions", response_model=list[ss.RegionOut], dependencies=[Depends(require_infra)])
def regions(db: Session = Depends(get_db)):
    return [ss.RegionOut.model_validate(r, from_attributes=True) for r in db.query(Region).order_by(Region.priority.asc()).all()]


@router.patch("/regions/{code}", response_model=ss.RegionOut, dependencies=[Depends(require_infra)])
def update_region(code: str, payload: s.RegionCreate, db: Session = Depends(get_db)):
    r = db.query(Region).filter(Region.code == code).first()
    if not r:
        raise NotFoundError("Region not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return ss.RegionOut.model_validate(r, from_attributes=True)


@router.get("/nodes", response_model=list[ss.NodeOut], dependencies=[Depends(require_infra)])
def nodes(db: Session = Depends(get_db)):
    return [ss.NodeOut.model_validate(n, from_attributes=True) for n in db.query(PterodactylNode).order_by(PterodactylNode.name.asc()).all()]


@router.patch("/nodes/{node_id}", response_model=ss.NodeOut, dependencies=[Depends(require_infra)])
def update_node(node_id: str, payload: s.NodeCreate, db: Session = Depends(get_db)):
    n = db.query(PterodactylNode).filter(PterodactylNode.id == node_id).first()
    if not n:
        raise NotFoundError("Node not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(n, k, v)
    db.commit()
    db.refresh(n)
    return ss.NodeOut.model_validate(n, from_attributes=True)


@router.get("/templates", response_model=list[ss.TemplateOut], dependencies=[Depends(require_infra)])
def templates(db: Session = Depends(get_db)):
    return [ss.TemplateOut.model_validate(t, from_attributes=True) for t in db.query(ServerTemplate).order_by(ServerTemplate.software.asc()).all()]


@router.patch("/templates/{template_id}", response_model=ss.TemplateOut, dependencies=[Depends(require_infra)])
def update_template(template_id: str, payload: s.TemplateCreate, db: Session = Depends(get_db)):
    t = db.query(ServerTemplate).filter(ServerTemplate.id == template_id).first()
    if not t:
        raise NotFoundError("Template not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return ss.TemplateOut.model_validate(t, from_attributes=True)


@router.get("/upgrade-prices", response_model=list[ss.UpgradePriceOut], dependencies=[Depends(require_infra)])
def upgrade_prices(db: Session = Depends(get_db)):
    return [ss.UpgradePriceOut.model_validate(p, from_attributes=True) for p in db.query(UpgradePrice).order_by(UpgradePrice.upgrade_type.asc()).all()]
