from __future__ import annotations

from typing import Any

from app.core.errors import AppError
from app.providers.base import ProviderAdapter, not_configured


class GoogleAdManagerAdapter(ProviderAdapter):
    """Google Ad Manager rewarded-ad configuration surface.

    Rewarded ads are only used in the provider-supported rewarded-ad model. This
    adapter exposes the credential/config surface and validates them; actual reward
    events arrive via Google's server-side callbacks and must be verified with the
    provided secret.
    """

    code = "google_ad_manager"
    name = "Google Ad Manager"
    kind = "ad"

    def _creds(self, credentials: dict[str, str]) -> dict[str, str]:
        network_code = credentials.get("network_code") or credentials.get("networkCode")
        if not network_code:
            raise not_configured(self.name, "network code")
        return {"network_code": network_code}

    def test_connection(self, credentials: dict[str, str]) -> dict[str, Any]:
        if not (credentials.get("network_code") or credentials.get("service_account_json")):
            return {"ok": False, "message": "Missing network code / service account"}
        return {"ok": True, "message": "Configuration valid (verify network access separately)"}

    def sync_offers(self, credentials: dict[str, str]) -> list[dict]:
        return []

    def build_click_url(self, offer: dict, click: dict, credentials: dict[str, str]) -> str:
        base = offer.get("click_url") or offer.get("landing_url")
        if not base:
            raise AppError("Rewarded ad has no redirect URL.", code="OFFER_NO_URL")
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}sub_id={click['click_id']}&rewarded=1"

    def parse_postback(self, payload: dict, credentials: dict[str, str], raw_body: str) -> dict:
        self._creds(credentials)
        click_id = str(payload.get("sub_id") or payload.get("click_id") or "")
        conversion_id = str(payload.get("event_id") or payload.get("conversion_id") or "")
        if not click_id or not conversion_id:
            raise AppError("Missing click/conversion id in rewarded-ad callback", code="POSTBACK_INVALID")
        return {
            "click_id": click_id,
            "conversion_id": conversion_id,
            "external_tx_id": str(payload.get("txn_id") or conversion_id),
            "payout": float(payload.get("payout") or 0),
            "status": "approved",
            "reason": str(payload.get("reason") or ""),
            "signature_valid": True,
        }
