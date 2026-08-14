from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings as env
from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.models.settings import SystemConfig

GLOBAL_KEY = "global"

DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "general": {
        "platform_name": "Cavrix Cloud",
        "logo_url": "",
        "favicon_url": "",
        "support_email": "support@cavrix.cloud",
        "timezone": "UTC",
        "currency": "INR",
        "currency_symbol": "₹",
        "default_language": "en",
    },
    "cvx": {
        "name": "CVX",
        "symbol": "CVX",
        "global_multiplier": 1.0,
        "min_reward": 50.0,
        "max_reward": 100000.0,
        "daily_limit": 5000.0,
        "hourly_limit": 1000.0,
        "max_balance": 100000.0,
        "default_task_multiplier": 1.0,
        "expiration_enabled": False,
        "expiration_days": 180,
    },
    "tasks": {
        "tasks_enabled": True,
        "offers_enabled": True,
        "min_account_age_days": 0,
        "task_cooldown_minutes": 0,
        "max_daily_tasks": 100,
    },
    "minecraft": {
        "server_claims_enabled": True,
        "min_cvx": 2500.0,
        "default_duration_days": 30,
        "max_servers_per_user": 3,
        "default_ram": 4096,
        "default_cpu": 2,
        "default_storage": 10240,
    },
    "pterodactyl": {
        "panel_url": "",
        "api_key_encrypted": "",
        "default_nest": "",
        "default_egg": "",
        "default_node": "",
        "client_api_enabled": True,
        "server_limits_override": "{}",
    },
    "referral": {
        "enabled": True,
        "reward": 250.0,
        "verification_required": True,
        "max_monthly": 10,
        "anti_abuse_threshold": 3,
        "campaign_multiplier": 1.0,
    },
    "maintenance": {
        "maintenance_mode": False,
        "maintenance_message": "Cavrix Cloud is under scheduled maintenance.",
        "scheduled_maintenance_at": "",
    },
    "fraud": {
        "vpn_proxy_penalty": 25,
        "impossible_completion_seconds": 45,
        "max_task_velocity_per_hour": 12,
        "max_devices_per_user": 4,
        "max_ips_per_user": 5,
        "same_device_conversion_limit": 3,
        "duplicate_ip_conversion_limit": 5,
        "referral_abuse_threshold": 3,
        "auto_hold_score": 60,
        "auto_reject_score": 80,
        "auto_ban_score": 95,
    },
    "ranking": {
        "payout_weight": 0.4,
        "conversion_weight": 0.25,
        "approval_weight": 0.2,
        "reliability_weight": 0.15,
    },
}


def _merge(defaults: dict[str, Any], stored: dict[str, Any]) -> dict[str, Any]:
    merged = dict(defaults)
    for k, v in stored.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_config(db: Session) -> dict[str, dict[str, Any]]:
    row = db.query(SystemConfig).filter(SystemConfig.key == GLOBAL_KEY).first()
    if not row:
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        stored = json.loads(row.value)
    except Exception:
        stored = {}
    return _merge(DEFAULT_CONFIG, stored)


def _save_config(db: Session, cfg: dict[str, dict[str, Any]]) -> None:
    row = db.query(SystemConfig).filter(SystemConfig.key == GLOBAL_KEY).first()
    if not row:
        row = SystemConfig(key=GLOBAL_KEY, value="{}")
        db.add(row)
    row.value = json.dumps(cfg, ensure_ascii=False)
    db.commit()


def get_value(db: Session, key: str, default: Any = None) -> Any:
    """key like 'cvx.global_multiplier'"""
    section, _, name = key.partition(".")
    cfg = load_config(db)
    return cfg.get(section, {}).get(name, default)


def set_value(db: Session, key: str, value: Any, section: str | None = None) -> None:
    cfg = load_config(db)
    sec, _, name = key.partition(".")
    if section:
        sec = section
    cfg.setdefault(sec, {})[name] = value
    _save_config(db, cfg)


def update_section(db: Session, section: str, values: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cfg = load_config(db)
    cfg.setdefault(section, {}).update(values)
    _save_config(db, cfg)
    return cfg


def set_pterodactyl_api_key(db: Session, plain: str) -> None:
    cfg = load_config(db)
    cfg["pterodactyl"]["api_key_encrypted"] = encrypt_secret(plain)
    _save_config(db, cfg)


def get_pterodactyl_api_key(db: Session) -> str:
    enc = get_value(db, "pterodactyl.api_key_encrypted", "")
    return decrypt_secret(enc) if enc else ""


def public_config(db: Session) -> dict[str, Any]:
    """Non-secret subset safe to expose to any frontend."""
    cfg = load_config(db)
    public = {
        "general": {
            "platform_name": cfg["general"]["platform_name"],
            "logo_url": cfg["general"]["logo_url"],
            "favicon_url": cfg["general"]["favicon_url"],
            "support_email": cfg["general"]["support_email"],
            "currency": cfg["general"]["currency"],
            "currency_symbol": cfg["general"]["currency_symbol"],
            "default_language": cfg["general"]["default_language"],
        },
        "cvx": {
            "name": cfg["cvx"]["name"],
            "symbol": cfg["cvx"]["symbol"],
            "daily_limit": cfg["cvx"]["daily_limit"],
            "hourly_limit": cfg["cvx"]["hourly_limit"],
            "max_balance": cfg["cvx"]["max_balance"],
        },
        "tasks": {
            "tasks_enabled": cfg["tasks"]["tasks_enabled"],
            "offers_enabled": cfg["tasks"]["offers_enabled"],
        },
        "minecraft": {
            "server_claims_enabled": cfg["minecraft"]["server_claims_enabled"],
            "min_cvx": cfg["minecraft"]["min_cvx"],
            "max_servers_per_user": cfg["minecraft"]["max_servers_per_user"],
            "default_duration_days": cfg["minecraft"]["default_duration_days"],
        },
        "referral": {
            "enabled": cfg["referral"]["enabled"],
            "reward": cfg["referral"]["reward"],
            "verification_required": cfg["referral"]["verification_required"],
            "max_monthly": cfg["referral"]["max_monthly"],
        },
        "maintenance": {
            "maintenance_mode": cfg["maintenance"]["maintenance_mode"],
            "maintenance_message": cfg["maintenance"]["maintenance_message"],
            "scheduled_maintenance_at": cfg["maintenance"]["scheduled_maintenance_at"],
        },
        "ranking": cfg["ranking"],
        "pterodactyl": {
            "panel_url": cfg["pterodactyl"]["panel_url"],
            "client_api_enabled": cfg["pterodactyl"]["client_api_enabled"],
            "configured": bool(cfg["pterodactyl"]["api_key_encrypted"]),
        },
    }
    return public
