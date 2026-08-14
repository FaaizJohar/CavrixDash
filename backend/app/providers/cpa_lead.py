from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx

from app.core.errors import AppError
from app.providers.base import ProviderAdapter, not_configured

_BASE = "https://api.cpalead.com/v1"


class CPAleadAdapter(ProviderAdapter):
    code = "cpa_lead"
    name = "CPAlead"
    kind = "offerwall"

    def _creds(self, credentials: dict[str, str]) -> dict[str, str]:
        api_key = credentials.get("api_key") or credentials.get("API key")
        secret = credentials.get("secret_key") or credentials.get("secret")
        if not api_key:
            raise not_configured(self.name)
        return {"api_key": api_key, "secret_key": secret or ""}

    def test_connection(self, credentials: dict[str, str]) -> dict[str, Any]:
        api_key = credentials.get("api_key")
        if not api_key:
            return {"ok": False, "message": "Missing API key"}
        try:
            resp = httpx.get(
                f"{_BASE}/offers",
                params={"api_key": api_key, "limit": 1},
                timeout=10,
            )
            if resp.status_code in (200, 201):
                return {"ok": True, "message": "Connected", "details": {"http": resp.status_code}}
            return {
                "ok": False,
                "message": f"API responded {resp.status_code}",
                "details": {"http": resp.status_code},
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def sync_offers(self, credentials: dict[str, str]) -> list[dict]:
        api_key = credentials.get("api_key")
        if not api_key:
            raise not_configured(self.name)
        try:
            resp = httpx.get(f"{_BASE}/offers", params={"api_key": api_key}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise AppError(f"CPAlead sync failed (HTTP {exc.response.status_code})", code="PROVIDER_SYNC_FAILED")
        except Exception as exc:
            raise AppError(f"CPAlead sync failed: {exc}", code="PROVIDER_SYNC_FAILED")

        offers = []
        for raw in (data.get("offers") or data.get("data") or []):
            n = self.normalize_offer(raw)
            n["click_url"] = raw.get("click_url") or raw.get("preview_url") or ""
            offers.append(n)
        return offers

    def build_click_url(self, offer: dict, click: dict, credentials: dict[str, str]) -> str:
        base = offer.get("click_url") or offer.get("landing_url")
        if not base:
            raise AppError("This offer has no click URL.", code="OFFER_NO_URL")
        token = click["token"]
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}sub1={click['click_id']}&sub2={token}"

    def parse_postback(self, payload: dict, credentials: dict[str, str], raw_body: str) -> dict:
        self._creds(credentials)
        click_id = str(payload.get("sub1") or payload.get("click_id") or payload.get("id") or "")
        conversion_id = str(
            payload.get("transaction_id")
            or payload.get("tid")
            or payload.get("conversion_id")
            or ""
        )
        status_raw = str(payload.get("status") or payload.get("event") or "approved").lower()
        payout = float(payload.get("payout") or payload.get("amount") or 0)

        if not click_id or not conversion_id:
            raise AppError("Missing click/conversion id in postback", code="POSTBACK_INVALID")

        status_map = {
            "approved": "approved",
            "complete": "approved",
            "rejected": "rejected",
            "reversal": "reversed",
            "reversed": "reversed",
            "chargeback": "reversed",
            "held": "held",
            "pending": "held",
        }
        status = status_map.get(status_raw, "approved")

        # signature check (HMAC-SHA256 over canonical fields, if secret configured)
        signature_valid = True
        secret = credentials.get("secret_key") or credentials.get("secret")
        if secret:
            msg = f"{click_id}:{conversion_id}:{payout}:{status_raw}"
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
