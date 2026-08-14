from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_client_meta, get_current_user
from app.core.errors import NotFoundError
from app.core.rate_limit import hit
from app.models.user import User
from app.schemas import auth as s
from app.schemas.common import Message
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(db, data: dict) -> s.TokenResponse:
    return s.TokenResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_in=settings.access_token_expire_minutes * 60,
        user=s.UserMe.model_validate(user_service.to_me(db, data["user"])),
    )


@router.post("/register", response_model=s.RegisterResponse)
def register(payload: s.RegisterRequest, request: Request, db: Session = Depends(get_db)):
    hit("auth", request.client.host if request.client else "x", settings.rate_limit_auth_per_min)
    user, requires_verification = auth_service.register(
        db,
        {
            "email": payload.email,
            "username": payload.username,
            "password": payload.password,
            "display_name": payload.display_name,
            "referral_code": payload.referral_code or "",
        },
        get_client_meta(request)["ip"],
    )
    return s.RegisterResponse(
        user=s.UserOut.model_validate(user, from_attributes=True),
        requires_verification=requires_verification,
        message="Account created. Check your email to verify." if requires_verification else "Account created.",
    )


@router.post("/verify-email/{token}", response_model=Message)
def verify_email(token: str, db: Session = Depends(get_db)):
    auth_service.verify_email(db, token)
    return Message(message="Email verified.")


@router.post("/login")
def login(payload: s.LoginRequest, request: Request, db: Session = Depends(get_db)):
    hit("auth", request.client.host if request.client else "x", settings.rate_limit_auth_per_min)
    device = {
        "device_id": payload.device_id,
        "device_name": payload.device_name,
        "user_agent": request.headers.get("user-agent", ""),
    }
    data = auth_service.login(db, payload.email, payload.password, device, get_client_meta(request)["ip"])
    if data.get("requires_2fa"):
        resp: dict = {"requires_2fa": True, "login_token": data["login_token"]}
        if data.get("mfa_setup_required"):
            resp["mfa_setup_required"] = True
            resp["setup"] = data["setup"]
        return resp
    return _token_response(db, data)


@router.post("/login/2fa")
def login_2fa(payload: s.TwoFaLoginRequest, request: Request, db: Session = Depends(get_db)):
    device = {
        "device_id": None,
        "device_name": None,
        "user_agent": request.headers.get("user-agent", ""),
    }
    data = auth_service.verify_2fa(db, payload.login_token, payload.code, device, get_client_meta(request)["ip"])
    return _token_response(db, data)


@router.post("/login/2fa/setup", response_model=s.TwoFaSetupLoginResponse)
def login_2fa_setup(payload: s.TwoFaSetupLoginRequest, request: Request, db: Session = Depends(get_db)):
    device = {
        "device_id": None,
        "device_name": None,
        "user_agent": request.headers.get("user-agent", ""),
    }
    data = auth_service.complete_setup_2fa(
        db, payload.login_token, payload.secret, payload.code, device, get_client_meta(request)["ip"]
    )
    return s.TwoFaSetupLoginResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_in=settings.access_token_expire_minutes * 60,
        user=s.UserMe.model_validate(user_service.to_me(db, data["user"])),
        backup_codes=data["backup_codes"],
    )


@router.post("/refresh", response_model=s.TokenResponse)
def refresh(payload: s.RefreshRequest, db: Session = Depends(get_db)):
    data = auth_service.refresh(db, payload.refresh_token)
    return _token_response(db, data)


@router.post("/step-up", response_model=s.StepUpResponse)
def step_up(payload: s.StepUpRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    token = auth_service.step_up(db, user, payload.password, payload.totp_code)
    return s.StepUpResponse(
        step_up_token=token,
        expires_in=settings.step_up_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=Message)
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    
    auth = request.headers.get("authorization", "")
    try:
        from app.core.security import decode_token

        payload = decode_token(auth[7:])
        auth_service.logout(db, payload.get("sid", ""))
    except Exception:
        pass
    return Message(message="Logged out.")


@router.get("/me", response_model=s.UserMe)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return s.UserMe.model_validate(user_service.to_me(db, user))


@router.post("/forgot-password", response_model=Message)
def forgot_password(payload: s.ForgotPasswordRequest, db: Session = Depends(get_db)):
    
    auth_service.forgot_password(db, payload.email)
    return Message(message="If that email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=Message)
def reset_password(payload: s.ResetPasswordRequest, db: Session = Depends(get_db)):
    
    auth_service.reset_password(db, payload.token, payload.password)
    return Message(message="Password updated. Please log in again.")


@router.get("/sessions", response_model=list[s.SessionOut])
def sessions(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    current_sid = ""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        from app.core.security import decode_token

        try:
            current_sid = decode_token(auth[7:]).get("sid", "")
        except Exception:
            current_sid = ""
    return auth_service.list_sessions(db, user.id, current_sid)


@router.delete("/sessions/{session_id}", response_model=Message)
def revoke_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    
    auth_service.revoke_session(db, user.id, session_id)
    return Message(message="Session revoked.")


@router.get("/2fa/setup", response_model=s.TwoFaSetupResponse)
def setup_2fa(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return auth_service.setup_2fa(db, user)


@router.post("/2fa/enable", response_model=Message)
def enable_2fa(payload: s.TwoFaEnableRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    
    auth_service.enable_2fa(db, user, payload.secret, payload.code)
    return Message(message="Two-factor authentication enabled.")


@router.post("/2fa/disable", response_model=Message)
def disable_2fa(payload: s.TwoFaDisableRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    
    auth_service.disable_2fa(db, user, payload.password)
    return Message(message="Two-factor authentication disabled.")


@router.get("/security", response_model=s.SecurityState)
def security(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.auth_service import list_sessions

    return s.SecurityState(
        email_verified=user.email_verified,
        twofa_enabled=user.twofa_enabled,
        has_backup_codes=bool(user.backup_codes and user.backup_codes != "[]"),
        password_last_changed=user.updated_at,
        sessions=list_sessions(db, user.id, ""),
    )
