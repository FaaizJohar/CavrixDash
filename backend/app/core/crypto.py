from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.encryption_key.encode()
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key)
    except Exception:
        raise RuntimeError("ENCRYPTION_KEY must be a valid Fernet key")


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise RuntimeError("Failed to decrypt secret (key mismatch?)")


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return "•" * 8 + value[-4:]
