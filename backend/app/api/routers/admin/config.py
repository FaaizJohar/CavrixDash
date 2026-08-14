from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_finance, require_infra, require_super_admin, verify_step_up
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas import admin as s
from app.services import settings_service as settings

router = APIRouter(prefix="/admin", tags=["admin"])

SECTION_LABELS = {
    "general": "Platform",
    "support": "Support",
    "payouts": "Payouts",
    "security": "Security",
}


def _flatten(cfg: dict, section: str) -> list[dict]:
    return [
        {"key": f"{section}.{k}", "label": label_for(section, k), "value": str(v), "section": section}
        for k, v in cfg.get(section, {}).items()
        if not isinstance(v, (dict, list))
    ]


def label_for(section: str, key: str) -> str:
    return " ".join(key.replace("_", " ").title().split())


@router.get("/settings", response_model=list[dict], dependencies=[Depends(require_finance)])
def get_settings(db: Session = Depends(get_db)):
    cfg = settings.load_config(db)
    out = []
    for section in ("general", "support", "payouts", "security", "cvx", "tasks", "minecraft", "referral", "fraud", "maintenance"):
        if section in cfg:
            out.extend(_flatten(cfg, section))
    return out


@router.patch("/settings", response_model=dict, dependencies=[Depends(require_finance)])
def update_settings(payload: s.SettingsUpdate, db: Session = Depends(get_db)):
    values = payload.settings
    secret_keys = {
        "pterodactyl.api_key_encrypted",
        "pterodactyl.panel_secret",
    }
    blocked = [k for k in values if k in secret_keys or "encrypted" in k.lower() or "secret" in k.lower() or "api_key" in k.lower()]
    if blocked:
        from app.core.errors import ForbiddenError

        raise ForbiddenError(
            f"Use the secrets endpoint to update: {', '.join(blocked)}.",
            code="SECRET_VIA_SETTINGS",
        )
    for key, value in values.items():
        section = key.split(".")[0]
        settings.set_value(db, key, value, section=section)
    return {"ok": True, "updated": list(values.keys())}


@router.get("/secrets", response_model=list[dict])
def list_secrets(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_super_admin)):
    verify_step_up(request, admin)
    cfg = settings.load_config(db)
    rows = []
    for k in ("pterodactyl.api_key_encrypted",):
        set_val = bool(cfg.get("pterodactyl", {}).get("api_key_encrypted"))
        rows.append({"key": k, "label": "Pterodactyl Application API Key", "masked": "••••••••" if set_val else "", "set": set_val, "last_rotated_at": ""})
    from app.models.provider import Provider, ProviderCredential

    providers = db.query(Provider).all()
    for p in providers:
        creds = db.query(ProviderCredential).filter(ProviderCredential.provider_id == p.id).all()
        for c in creds:
            rows.append({
                "key": f"provider.{p.code}.{c.name}",
                "label": f"{p.name} — {c.name}",
                "masked": c.masked or ("••••••••" if c.value_encrypted else ""),
                "set": bool(c.value_encrypted),
                "last_rotated_at": c.rotated_at,
            })
    return rows


@router.post("/secrets", response_model=dict)
def update_secrets(payload: dict, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_super_admin)):
    verify_step_up(request, admin)
    from app.services import provider_service

    updated = []
    for key, value in payload.items():
        if not value:
            continue
        if key == "pterodactyl.api_key_encrypted":
            settings.set_pterodactyl_api_key(db, str(value))
            updated.append(key)
        elif key.startswith("provider."):
            parts = key.split(".")
            if len(parts) >= 3:
                code, cred_name = parts[1], ".".join(parts[2:])
                p = provider_service.get_by_code(db, code)
                if p:
                    provider_service.set_credentials(db, p, {cred_name: str(value)})
                    updated.append(key)
    return {"ok": True, "updated": updated}


@router.post("/pterodactyl/test", response_model=dict, dependencies=[Depends(require_infra)])
def test_pterodactyl(db: Session = Depends(get_db)):
    from app.services import pterodactyl_service

    return pterodactyl_service.test_connection(db)
