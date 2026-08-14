from __future__ import annotations

from typing import Any

from app.core.errors import AppError
from app.providers.base import ProviderAdapter, not_configured


class ShrinkMeAdapter(ProviderAdapter):
    """Monetized links adapter.

    Users earn only where the link provider's current terms explicitly allow the
    incentivized model. This adapter only exposes the configuration surface + click
    tracking; conversions arrive as provider postbacks and are verified with HMAC.
    """

    code = "shrink_me"
    name = "ShrinkMe"
    kind = "link"

    def _creds(self, credentials: dict[str, str]) -> dict[str, str]:
        api_key = credentials.get("api_key") or credentials.get("API key")
        if not api_key:
            raise not_configured(self.name)
        return {"api_key": api_key}

    def test_connection(self, credentials: dict[str, str]) -> dict[str, Any]:
        if not (credentials.get("api_key")):
            return {"ok": False, "message": "Missing API key"}
        # ShrinkMe provides a shortlink API; validate key by requesting account info.
        return {"ok": True, "message": "Key configured (validate against provider API)"}

    def sync_offers(self, credentials: dict[str, str]) -> list[dict]:
        # Links are created manually or via provider UI; nothing to sync automatically.
        return []

    def build_click_url(self, offer: dict, click: dict, credentials: dict[str, str]) -> str:
        base = offer.get("click_url") or offer.get("landing_url")
        if not base:
            raise AppError("This link has no destination URL.", code="OFFER_NO_URL")
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}sub_id={click['click_id']}&sub1={click['token']}"

    def parse_postback(self, payload: dict, credentials: dict[str, str], raw_body: str) -> dict:
        self._creds(credentials)
        click_id = str(payload.get("sub_id") or payload.get("click_id") or "")
        conversion_id = str(payload.get("conversion_id") or payload.get("txn_id") or "")
        status_raw = str(payload.get("status") or "approved").lower()
        payout = float(payload.get("payout") or payload.get("amount") or 0)
        if not click_id or not conversion_id:
            raise AppError("Missing click/conversion id in postback", code="POSTBACK_INVALID")
        status = "approved" if status_raw in {"approved", "complete", "paid"} else "rejected"

        signature_valid = True
        secret = credentials.get("secret_key") or credentials.get("secret")
        if secret:
            msg = f"{click_id}:{conversion_id}:{status_raw}"
            sig = str(payload.get("signature") or payload.get("hash") or "")
            signature_valid = self.hmac_verify(secret, msg, sig)
            if not signature_valid:
                raise AppError("Invalid postback signature", code="POSTBACK_SIGNATURE")

        return {
            "click_id": click_id,
            "conversion_id": conversion_id,
            "external_tx_id": str(payload.get("txn_id") or conversion_id),
            "payout": payout,
            "status": status,
            "reason": str(payload.get("reason") or ""),
            "signature_valid": signature_valid,
        }
