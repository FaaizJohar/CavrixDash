from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.pterodactyl.client import PterodactylClient
from app.services import settings_service as settings


def get_client(db: Session) -> PterodactylClient:
    panel_url = settings.get_value(db, "pterodactyl.panel_url", "")
    app_key = settings.get_pterodactyl_api_key(db)
    client_key = settings.get_value(db, "pterodactyl.client_api_key_encrypted", "")
    from app.core.crypto import decrypt_secret

    if not panel_url or not app_key:
        raise AppError(
            "Pterodactyl is not configured. Contact support.",
            code="PTERODACTYL_NOT_CONFIGURED",
            status_code=503,
        )
    client_plain = decrypt_secret(client_key) if client_key else ""
    return PterodactylClient(panel_url, app_key, client_plain)


def test_connection(db: Session) -> dict[str, Any]:
    panel_url = settings.get_value(db, "pterodactyl.panel_url", "")
    app_key = settings.get_pterodactyl_api_key(db)
    if not panel_url or not app_key:
        return {"ok": False, "message": "Panel URL / Application API key not configured."}
    try:
        client = PterodactylClient(panel_url, app_key, "")
        result = client.test()
        result["panel_url"] = panel_url
        result["status"] = "connected"
        return result
    except AppError as exc:
        return {"ok": False, "message": exc.message}


def ensure_panel_user(db: Session, user) -> int:
    """Create a Pterodactyl panel user for a Cavrix user on first server claim."""
    meta = json.loads(user.meta or "{}")
    if meta.get("panel_user_id"):
        return int(meta["panel_user_id"])
    client = get_client(db)
    attrs = client.create_user(
        email=user.email,
        username=user.username.lower().replace("_", "")[:31] or f"user{user.username}",
        first_name=user.display_name or user.username,
        last_name="",
    )
    pid = attrs.get("id")
    meta["panel_user_id"] = pid
    user.meta = json.dumps(meta)
    user.panel_user_id = str(pid)
    db.commit()
    return int(pid)


def server_identifier(server) -> str:
    meta = json.loads(server.meta or "{}")
    return meta.get("identifier") or server.pterodactyl_server_id
