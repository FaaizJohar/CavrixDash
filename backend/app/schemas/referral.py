from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ReferralSummary(BaseModel):
    code: str
    url: str
    reward: float
    total_invited: int
    verified: int
    rewarded: int
    pending: int
    earnings: float
    max_monthly: int
    referrals_this_month: int


class ReferralRow(ORMModel):
    id: str
    invitee_email: str
    status: str
    reward_amount: float
    rewarded_at: str
    risk_score: float
    created_at: Any = None
