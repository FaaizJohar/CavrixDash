from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel, Timestamped


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=80)
    referral_code: str | None = None


class RegisterResponse(BaseModel):
    user: "UserOut"
    requires_verification: bool
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str | None = None
    device_name: str | None = None


class TwoFaLoginRequest(BaseModel):
    login_token: str
    code: str


class MfaSetupInfo(BaseModel):
    secret: str
    uri: str
    qr_base64: str


class TwoFaSetupLoginRequest(BaseModel):
    login_token: str
    secret: str
    code: str


class TwoFaSetupLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserOut"
    backup_codes: list[str]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserOut"


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class TwoFaSetupResponse(BaseModel):
    secret: str
    uri: str
    qr_base64: str
    backup_codes: list[str]


class TwoFaEnableRequest(BaseModel):
    secret: str
    code: str


class TwoFaDisableRequest(BaseModel):
    password: str


class StepUpRequest(BaseModel):
    password: str
    totp_code: str = ""


class StepUpResponse(BaseModel):
    step_up_token: str
    expires_in: int


class SessionOut(ORMModel):
    id: str
    device_name: str
    ip: str
    created_at: Any = None
    last_seen_at: str = ""
    current: bool = False


class SecurityState(BaseModel):
    email_verified: bool
    twofa_enabled: bool
    has_backup_codes: bool
    password_last_changed: Any = None
    sessions: list[SessionOut]


class UserOut(Timestamped):
    id: str
    email: str
    username: str
    display_name: str
    avatar_url: str
    referral_code: str
    email_verified: bool
    twofa_enabled: bool
    status: str
    roles: list[str]
    created_at: Any = None

    @field_validator("roles", mode="before")
    @classmethod
    def _roles_str(cls, v: Any) -> Any:
        if isinstance(v, list) and v and not isinstance(v[0], str):
            return [r.name for r in v]
        return v


class UserMe(UserOut):
    cvx_balance: float
    cvx_lifetime_earned: float
    cvx_lifetime_spent: float
    tasks_completed: int
    conversions_approved: int
    conversions_pending: int
    active_servers: int
    server_limit: int
    is_super_admin: bool
    is_admin: bool


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=512)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    current_password: str | None = None
