from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# ---------------------------------------------------------------- JWT
def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    now = _now()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "tv": settings.token_version,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return create_token(
        subject,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        extra,
    )


def create_refresh_token(subject: str, session_id: str, token_hash: str) -> str:
    return create_token(
        subject,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
        {"sid": session_id, "th": token_hash},
    )


def create_step_up_token(subject: str) -> str:
    """Short-lived token proving fresh password (+2FA) confirmation for
    sensitive operations like CVX adjustments or secret reveals."""
    return create_token(
        subject,
        "step_up",
        timedelta(minutes=settings.step_up_token_expire_minutes),
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": True},
    )


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- TOTP (RFC 6238)
_TOTP_STEP = 30
_TOTP_DIGITS = 6


def generate_totp_secret() -> str:
    return base64.b32encode(bytearray(__import__("os").urandom(20))).decode()


def totp_uri(secret: str, label: str, issuer: str) -> str:
    return (
        f"otpauth://totp/{issuer}:{label}?secret={secret}"
        f"&issuer={issuer}&algorithm=SHA1&digits={_TOTP_DIGITS}&period={_TOTP_STEP}"
    )


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    try:
        code = code.strip()
        counter = int(time.time() // _TOTP_STEP)
        for off in range(-window, window + 1):
            expected = _totp_at(secret, counter + off)
            if hmac.compare_digest(expected, code):
                return True
    except Exception:
        return False
    return False


def _totp_at(secret: str, counter: int) -> str:
    key = base64.b32decode(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 10 ** _TOTP_DIGITS
    return str(code).zfill(_TOTP_DIGITS)


def generate_backup_codes(n: int = 10) -> list[str]:
    codes: list[str] = []
    for _ in range(n):
        raw = base64.b32encode(__import__("os").urandom(5)).decode()[:8]
        codes.append("-".join([raw[:4], raw[4:]]))
    return codes


def hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()
