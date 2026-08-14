from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import misc as s
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=s.OverviewStats)
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return analytics_service.overview(db, user)
