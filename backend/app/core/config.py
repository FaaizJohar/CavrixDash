from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_KEYS = {
    "change-me-generate-a-long-random-secret",
    "change-me",
    "",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Cavrix Cloud"
    app_env: str = "development"
    app_debug: bool = False
    app_timezone: str = "UTC"
    api_v1_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    public_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = Field(default="http://localhost:5173")

    # Security
    secret_key: str = "change-me-generate-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    token_version: int = 1
    secure_cookies: bool = False
    encryption_key: str = "change-me"
    session_cookie_name: str = "cavrix_session"
    step_up_token_expire_minutes: int = 5

    # Database
    database_url: str = "postgresql+psycopg://cavrix:cavrix@localhost:5432/cavrix"
    db_auto_create: bool = True

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate limits (per minute windows, redis-backed)
    rate_limit_auth_per_min: int = 10
    rate_limit_general_per_min: int = 120
    rate_limit_postback_per_min: int = 300
    rate_limit_server_create_per_min: int = 3
    rate_limit_server_action_per_min: int = 30

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@cavrix.cloud"
    smtp_tls: bool = True
    email_verification_required: bool = False

    # CVX economy defaults (overridable via DB settings)
    cvx_name: str = "CVX"
    cvx_symbol: str = "CVX"
    cvx_global_multiplier: float = 1.0
    cvx_max_balance: float = 100000.0
    cvx_daily_limit: float = 5000.0
    cvx_hourly_limit: float = 1000.0

    # Servers
    servers_max_per_user: int = 3
    servers_default_duration_days: int = 30
    servers_min_cvx: float = 2500.0

    # Referral
    referral_enabled: bool = True
    referral_reward: float = 250.0
    referral_verification_required: bool = True

    # Providers
    # Mock provider is a development-only fixture. MUST be explicitly enabled
    # via env in non-production environments; never enabled by default.
    mock_provider_enabled: bool = False
    # AdGem postback HMAC-SHA256 secret (v3 POST signature verification).
    adgem_postback_key: str = ""
    # Background offer-sync cadence (minutes). Each enabled provider is synced
    # at most once per interval.
    provider_sync_interval_minutes: int = 30
    # Exponential backoff parameters used when a provider sync fails.
    # Delay for the N-th consecutive failure = base * 2^(N-1), capped at max.
    provider_sync_error_base_seconds: int = 60
    provider_sync_max_backoff_minutes: int = 240

    # Bootstrap
    seed_admin_email: str = "admin@cavrix.cloud"
    seed_admin_password: str = "ChangeMe!12345"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @field_validator("app_env")
    @classmethod
    def _normalize_env(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def _enforce_prod_secrets(self) -> "Settings":
        if self.is_prod:
            if self.secret_key in _INSECURE_KEYS:
                raise ValueError("secret_key must be set to a strong value in production.")
            if self.encryption_key in _INSECURE_KEYS:
                raise ValueError("encryption_key must be set to a strong value in production.")
            if self.seed_admin_password in {"ChangeMe!12345", "", "change-me"}:
                raise ValueError("seed_admin_password must be overridden in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
