from __future__ import annotations

import hashlib
import hmac
from abc import ABC, abstractmethod
from typing import Any

from app.core.errors import AppError


class ProviderAdapter(ABC):
    code: str = ""
    name: str = ""
    kind: str = "offerwall"  # offerwall | ad | link | mock

    # ---------------------------------------------------------------- lifecycle
    @abstractmethod
    def test_connection(self, credentials: dict[str, str]) -> dict[str, Any]:
        """Return {'ok': bool, 'message': str, 'details': {...}}"""

    @abstractmethod
    def sync_offers(self, credentials: dict[str, str]) -> list[dict[str, Any]]:
        """Fetch offers from the provider API. Returns normalized offer dicts."""

    @abstractmethod
    def build_click_url(self, offer: dict[str, Any], click: dict[str, Any], credentials: dict[str, str]) -> str:
        """Build the outbound redirect URL for a tracked click."""

    @abstractmethod
    def parse_postback(self, payload: dict[str, Any], credentials: dict[str, str], raw_body: str) -> dict[str, Any]:
        """
        Validate + normalize a postback into:
        {
          'click_id': str, 'conversion_id': str, 'external_tx_id': str,
          'payout': float, 'status': 'approved'|'rejected'|'reversed'|'held',
          'reason': str, 'signature_valid': bool
        }
        Raise AppError if the postback is invalid.
        """

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def hmac_verify(secret: str, message: str, signature: str, algorithm: str = "sha256") -> bool:
        if not signature:
            return False
        digest = hmac.new(secret.encode(), message.encode(), getattr(hashlib, algorithm)).hexdigest()
        return hmac.compare_digest(digest.lower(), signature.lower())

    @staticmethod
    def normalize_offer(raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_id": str(raw.get("external_id") or raw.get("id") or ""),
            "title": str(raw.get("title") or ""),
            "description": str(raw.get("description") or ""),
            "category": str(raw.get("category") or "other"),
            "icon_url": str(raw.get("icon_url") or raw.get("logo") or ""),
            "reward": float(raw.get("reward") or raw.get("points") or 0),
            "payout": float(raw.get("payout") or raw.get("payout_amount") or 0),
            "estimated_time": int(raw.get("estimated_time") or raw.get("minutes") or 0),
            "countries": raw.get("countries") or [],
            "devices": raw.get("devices") or [],
            "requirements": str(raw.get("requirements") or ""),
            "conversion_event": str(raw.get("conversion_event") or "action"),
            "click_url": str(raw.get("click_url") or ""),
            "landing_url": str(raw.get("landing_url") or ""),
            "tracking_url": str(raw.get("tracking_url") or ""),
            "status": str(raw.get("status") or "active"),
            "payout_currency": str(raw.get("payout_currency") or "USD"),
            "meta": raw.get("meta") or {},
        }


def not_configured(name: str, key: str = "API key") -> AppError:
    return AppError(
        f"{name} is not configured. Add its {key} in Super Admin → Providers.",
        code="PROVIDER_NOT_CONFIGURED",
        status_code=503,
    )
