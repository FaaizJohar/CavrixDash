from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core import rate_limit
from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.core.errors import AppError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_step_up_token,
    decode_token,
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_code,
    hash_password,
    token_fingerprint,
    totp_uri,
    verify_password,
    verify_totp,
)
from app.models.auth import Session as SessionModel
from app.models.user import User
from app.services import email_service, user_service


class AuthError(AppError):
    pass


def register(db: Session, data: dict[str, Any], ip: str) -> tuple[User, bool]:
    user = user_service.create_user(
        db,
        email=data["email"],
        username=data["username"],
        password=data["password"],
        display_name=data.get("display_name", ""),
    )
    if data.get("referral_code"):
        from app.services import referral_service

        referrer = user_service.get_by_referral_code(db, data["referral_code"])
        if referrer and referrer.id != user.id:
            user.invited_by = referrer.id
            referral_service.create_referral(db, referrer, user, ip)
            db.commit()

    requires_verification = settings.email_verification_required
    if requires_verification:
        token = _email_token(user.id, "verify")
        link = f"{settings.frontend_url}/auth/verify-email?token={token}"
        email_service.send_verification_email(user.email, link)
    else:
        user.email_verified = True
        db.commit()
    return user, requires_verification


def _email_token(subject: str, purpose: str) -> str:
    from app.core.security import create_token

    return create_token(subject, purpose, timedelta(hours=24))


def verify_email(db: Session, token: str) -> None:
    try:
        payload = decode_token(token)
    except Exception:
        raise AppError("Invalid or expired verification link.", code="INVALID_TOKEN")
    if payload.get("type") != "verify":
        raise AppError("Invalid token type.", code="INVALID_TOKEN")
    user = user_service.get_by_id(db, payload["sub"])
    if not user:
        raise NotFoundError("User not found.")
    user.email_verified = True
    db.commit()


def login(db: Session, email: str, password: str, device: dict[str, Any] | None, ip: str) -> dict[str, Any]:
    user = user_service.get_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        rate_limit.incr(f"failed_login:{email}", 600)
        raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS")
    user_service.require_active(user)

    from app.services import fraud_service

    if fraud_service.check_login_risk(db, user, ip):
        raise ForbiddenError(
            "Suspicious login blocked. Verify your email or contact support.",
            code="LOGIN_BLOCKED",
        )

    if user.twofa_enabled:
        token = _email_token(user.id, "2fa_pending")
        return {"requires_2fa": True, "login_token": token, "user": None}

    if user.requires_mandatory_mfa:
        # MFA is mandatory for privileged admins. They cannot finish logging in
        # until 2FA is configured and verified during this attempt.
        token = _email_token(user.id, "2fa_setup_pending")
        return {
            "requires_2fa": True,
            "mfa_setup_required": True,
            "login_token": token,
            "setup": _mfa_setup_payload(generate_totp_secret(), user.email),
            "user": None,
        }

    return _complete_login(db, user, device, ip)


def _complete_login(db: Session, user: User, device: dict[str, Any] | None, ip: str) -> dict[str, Any]:
    device = device or {}
    device_id = device.get("device_id") or f"dev-{secrets.token_hex(8)}"
    device_name = device.get("device_name") or _guess_device(device)
    user_agent = device.get("user_agent", "")

    session, access, refresh = _issue_session(db, user, device_id, device_name, ip, user_agent)
    user.last_login_at = datetime.now(timezone.utc).isoformat()
    user.last_login_ip = ip
    db.commit()

    return {
        "requires_2fa": False,
        "user": user,
        "session": session,
        "access_token": access,
        "refresh_token": refresh,
    }


def verify_2fa(db: Session, login_token: str, code: str, device: dict[str, Any] | None, ip: str) -> dict[str, Any]:
    try:
        payload = decode_token(login_token)
    except Exception:
        raise AppError("2FA session expired. Please log in again.", code="LOGIN_EXPIRED")
    if payload.get("type") != "2fa_pending":
        raise AppError("Invalid 2FA token.", code="LOGIN_EXPIRED")
    user = user_service.get_by_id(db, payload["sub"])
    if not user:
        raise NotFoundError("User not found.")

    if user.twofa_secret and verify_totp(user.twofa_secret, code):
        return _complete_login(db, user, device, ip)

    for stored in json.loads(user.backup_codes or "[]"):
        if hash_backup_code(code.strip()) == stored:
            return _complete_login(db, user, device, ip)
    raise UnauthorizedError("Invalid 2FA code.", code="INVALID_2FA")


def complete_setup_2fa(
    db: Session,
    login_token: str,
    secret: str,
    code: str,
    device: dict[str, Any] | None,
    ip: str,
) -> dict[str, Any]:
    """Finishes the mandatory MFA bootstrap for a super admin mid-login.

    The user must prove they hold the freshly generated TOTP secret shown on
    the setup screen (or the login would be deadlocked). On success 2FA is
    enabled and the login completes.
    """
    try:
        payload = decode_token(login_token)
    except Exception:
        raise AppError("2FA setup session expired. Please log in again.", code="LOGIN_EXPIRED")
    if payload.get("type") != "2fa_setup_pending":
        raise AppError("Invalid 2FA setup session.", code="LOGIN_EXPIRED")
    user = user_service.get_by_id(db, payload["sub"])
    if not user:
        raise NotFoundError("User not found.")

    if not secret or not verify_totp(secret, code):
        raise UnauthorizedError("Invalid 2FA code.", code="INVALID_2FA")

    backup = generate_backup_codes()
    user.twofa_secret = secret
    user.twofa_enabled = True
    user.backup_codes = json.dumps([hash_backup_code(c) for c in backup])
    db.commit()

    data = _complete_login(db, user, device, ip)
    data["backup_codes"] = backup
    return data


def _issue_session(
    db: Session, user: User, device_id: str, device_name: str, ip: str, user_agent: str
) -> tuple[SessionModel, str, str]:
    session = SessionModel(
        user_id=user.id,
        refresh_token_hash="",
        device_id=device_id,
        device_name=device_name,
        ip=ip,
        user_agent=user_agent,
        expires_at=(datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)).isoformat(),
        last_seen_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(session)
    db.flush()
    refresh = create_refresh_token(user.id, session.id, "x")
    session.refresh_token_hash = token_fingerprint(refresh)
    db.flush()
    access = create_access_token(user.id, {"sid": session.id})
    db.commit()
    return session, access, refresh


def refresh(db: Session, refresh_token: str) -> dict[str, Any]:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise UnauthorizedError("Session expired. Please log in again.", code="TOKEN_EXPIRED")
    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token.", code="TOKEN_EXPIRED")
    sid = payload.get("sid")
    session = db.query(SessionModel).filter(SessionModel.id == sid).first()
    if not session or session.revoked or not session.is_active():
        raise UnauthorizedError("Session expired. Please log in again.", code="TOKEN_EXPIRED")
    if session.refresh_token_hash != token_fingerprint(refresh_token):
        session.revoked = True
        db.commit()
        raise UnauthorizedError("Session expired. Please log in again.", code="TOKEN_EXPIRED")
    user = user_service.get_by_id(db, session.user_id)
    if not user:
        raise NotFoundError("User not found.")
    user_service.require_active(user)

    new_refresh = create_refresh_token(user.id, session.id, "x")
    session.refresh_token_hash = token_fingerprint(new_refresh)
    session.last_seen_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    access = create_access_token(user.id, {"sid": session.id})
    return {"access_token": access, "refresh_token": new_refresh, "user": user}


def step_up(db: Session, user: User, password: str, totp_code: str = "") -> str:
    """Re-confirms the account's first (password) and, when enabled, second
    (TOTP/backup) factor, returning a short-lived step-up token."""
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("Incorrect password.", code="INVALID_CREDENTIALS")
    if user.twofa_enabled:
        code_ok = bool(user.twofa_secret and verify_totp(user.twofa_secret, totp_code))
        if not code_ok:
            for stored in json.loads(user.backup_codes or "[]"):
                if hash_backup_code(totp_code.strip()) == stored:
                    code_ok = True
                    break
        if not code_ok:
            raise UnauthorizedError("Invalid 2FA code.", code="INVALID_2FA")
    return create_step_up_token(user.id)


def logout(db: Session, session_id: str) -> None:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session:
        session.revoked = True
        db.commit()


def revoke_session(db: Session, user_id: str, session_id: str) -> None:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session and session.user_id == user_id:
        session.revoked = True
        db.commit()


def list_sessions(db: Session, user_id: str, current_sid: str) -> list[dict[str, Any]]:
    rows = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": s.id,
            "device_name": s.device_name,
            "ip": s.ip,
            "created_at": s.created_at,
            "last_seen_at": s.last_seen_at,
            "current": s.id == current_sid,
            "revoked": s.revoked,
        }
        for s in rows
    ]


def forgot_password(db: Session, email: str) -> None:
    user = user_service.get_by_email(db, email)
    if not user:
        return
    token = _email_token(user.id, "reset")
    link = f"{settings.frontend_url}/auth/reset-password?token={token}"
    email_service.send_reset_email(user.email, link)


def reset_password(db: Session, token: str, password: str) -> None:
    try:
        payload = decode_token(token)
    except Exception:
        raise AppError("Invalid or expired reset link.", code="INVALID_TOKEN")
    if payload.get("type") != "reset":
        raise AppError("Invalid token type.", code="INVALID_TOKEN")
    user = user_service.get_by_id(db, payload["sub"])
    if not user:
        raise NotFoundError("User not found.")
    user.password_hash = hash_password(password)
    for s in db.query(SessionModel).filter(SessionModel.user_id == user.id, SessionModel.revoked == False):  # noqa: E712
        s.revoked = True
    db.commit()


def _mfa_setup_payload(secret: str, email: str) -> dict[str, Any]:
    uri = totp_uri(secret, email, settings.app_name)
    from qrcode import QRCode

    qr = QRCode(border=1, box_size=8)
    qr.add_data(uri)
    qr.make(fit=True)
    import base64
    import io

    buf = io.BytesIO()
    qr.make_image().save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return {"secret": secret, "uri": uri, "qr_base64": qr_b64}


def setup_2fa(db: Session, user: User) -> dict[str, Any]:
    secret = user.twofa_secret or generate_totp_secret()
    user.twofa_secret = secret
    db.commit()
    payload = _mfa_setup_payload(secret, user.email)
    backup = generate_backup_codes()
    payload["backup_codes"] = backup
    return payload


def enable_2fa(db: Session, user: User, secret: str, code: str) -> None:
    if not verify_totp(secret, code):
        raise AppError("Invalid verification code.", code="INVALID_2FA")
    backup = generate_backup_codes()
    user.twofa_secret = secret
    user.twofa_enabled = True
    user.backup_codes = json.dumps([hash_backup_code(c) for c in backup])
    db.commit()


def disable_2fa(db: Session, user: User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise AppError("Incorrect password.", code="INVALID_CREDENTIALS")
    if user.requires_mandatory_mfa:
        raise ForbiddenError(
            "Two-factor authentication is mandatory for administrator accounts and cannot be disabled.",
            code="MFA_REQUIRED",
        )
    user.twofa_enabled = False
    user.twofa_secret = ""
    user.backup_codes = "[]"
    db.commit()


def _guess_device(device: dict[str, Any]) -> str:
    ua = (device.get("user_agent") or "").lower()
    if "android" in ua:
        return "Android device"
    if "iphone" in ua or "ipad" in ua:
        return "iOS device"
    if "windows" in ua:
        return "Windows PC"
    if "mac" in ua:
        return "Mac"
    if "linux" in ua:
        return "Linux"
    return "Unknown device"
