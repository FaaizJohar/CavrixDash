from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.providers.base import ProviderAdapter

_SAMPLE_OFFERS = [
    {
        "external_id": "mock-game-challenge",
        "title": "Game Challenge",
        "description": "Install the game and complete level 5 to earn CVX. Legitimate in-game progress only.",
        "category": "games",
        "icon_url": "",
        "reward": 900,
        "payout": 0.60,
        "estimated_time": 15,
        "countries": ["IN", "US", "GB", "AE"],
        "devices": ["android", "ios"],
        "requirements": "Install from the official store and reach level 5.",
        "conversion_event": "level_5_reached",
        "click_url": "https://example.mock/destination?offer=game-challenge",
    },
    {
        "external_id": "mock-saas-trial",
        "title": "SaaS Trial",
        "description": "Start a free trial of a productivity suite and keep the account active for 7 days.",
        "category": "trials",
        "icon_url": "",
        "reward": 1500,
        "payout": 1.20,
        "estimated_time": 60,
        "countries": ["US", "GB", "IN"],
        "devices": ["web"],
        "requirements": "Register with a valid email and verify the account.",
        "conversion_event": "trial_active_7d",
        "click_url": "https://example.mock/destination?offer=saas-trial",
    },
    {
        "external_id": "mock-app-registration",
        "title": "App Registration",
        "description": "Create a real account in a partner app and verify your email address.",
        "category": "cpi",
        "icon_url": "",
        "reward": 400,
        "payout": 0.35,
        "estimated_time": 5,
        "countries": ["IN", "PH", "ID"],
        "devices": ["android"],
        "requirements": "New account only. Verification required.",
        "conversion_event": "registration_complete",
        "click_url": "https://example.mock/destination?offer=app-registration",
    },
    {
        "external_id": "mock-survey",
        "title": "Market Survey",
        "description": "Complete a short market research survey (10 minutes).",
        "category": "surveys",
        "icon_url": "",
        "reward": 250,
        "payout": 0.20,
        "estimated_time": 10,
        "countries": ["US", "GB", "CA", "IN"],
        "devices": ["web", "android", "ios"],
        "requirements": "Answer all questions truthfully.",
        "conversion_event": "survey_complete",
        "click_url": "https://example.mock/destination?offer=survey",
    },
    {
        "external_id": "mock-cpa-signup",
        "title": "Finance App Signup",
        "description": "Open and verify a demo trading account (no deposit needed).",
        "category": "cpa",
        "icon_url": "",
        "reward": 1200,
        "payout": 0.95,
        "estimated_time": 20,
        "countries": ["US", "GB", "AU"],
        "devices": ["web", "ios"],
        "requirements": "Full KYC verification required by partner.",
        "conversion_event": "account_verified",
        "click_url": "https://example.mock/destination?offer=cpa-signup",
    },
]


class MockProviderAdapter(ProviderAdapter):
    """Development-only provider. NEVER enable in production."""

    code = "mock"
    name = "Mock (Development Only)"
    kind = "offerwall"

    def _ensure_dev(self) -> None:
        if not settings.mock_provider_enabled:
            from app.core.errors import AppError

            raise AppError("Mock provider is disabled.", code="PROVIDER_DISABLED", status_code=503)

    def test_connection(self, credentials: dict[str, str]) -> dict[str, Any]:
        return {"ok": True, "message": "Mock provider ready (dev only)", "details": {"dev": True}}

    def sync_offers(self, credentials: dict[str, str]) -> list[dict]:
        self._ensure_dev()
        return [self.normalize_offer(o) for o in _SAMPLE_OFFERS]

    def build_click_url(self, offer: dict, click: dict, credentials: dict[str, str]) -> str:
        base = offer.get("click_url") or "https://example.mock/destination"
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}sub1={click['click_id']}&sub2={click['token']}&cvx_mock=1"

    def parse_postback(self, payload: dict, credentials: dict[str, str], raw_body: str) -> dict:
        self._ensure_dev()
        click_id = str(payload.get("sub1") or payload.get("click_id") or "")
        conversion_id = str(
            payload.get("conversion_id") or payload.get("tid") or f"mock-{click_id}"
        )
        status_raw = str(payload.get("status") or "approved").lower()
        payout = float(payload.get("payout") or 0)
        status_map = {
            "approved": "approved",
            "rejected": "rejected",
            "reversed": "reversed",
            "hold": "held",
        }
        return {
            "click_id": click_id,
            "conversion_id": conversion_id,
            "external_tx_id": str(payload.get("txn_id") or conversion_id),
            "payout": payout,
            "status": status_map.get(status_raw, "approved"),
            "reason": str(payload.get("reason") or ""),
            "signature_valid": True,
        }
