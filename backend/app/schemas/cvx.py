from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ConversionOut(ORMModel):
    id: str
    click_id: str
    offer_id: str
    offer_title: str = ""
    provider_code: str = ""
    conversion_id: str
    status: str
    reward_amount: float
    risk_score: float
    created_at: Any = None
    updated_at: Any = None


class WalletOut(BaseModel):
    balance: float
    lifetime_earned: float
    lifetime_spent: float
    daily_limit: float
    hourly_limit: float
    max_balance: float
    earned_today: float
    earned_this_hour: float


class LedgerEntry(ORMModel):
    id: str
    transaction_type: str
    amount: float
    balance_after: float
    reference_type: str = ""
    reference_id: str = ""
    description: str = ""
    created_at: Any = None


class CvxRuleOut(ORMModel):
    key: str
    value: str
    kind: str
    label: str
    section: str
