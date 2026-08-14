import time

import pytest

from app.core.database import SessionLocal
from app.core.security import _totp_at
from app.models.user import User


def _reset_super_2fa() -> None:
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == "super@test.io").first()
        u.twofa_enabled = False
        u.twofa_secret = ""
        u.backup_codes = "[]"
        db.commit()
    finally:
        db.close()


def _current_totp(secret: str) -> str:
    return _totp_at(secret, int(time.time() // 30))


def _super_headers(client) -> dict[str, str]:
    """Completes the mandatory setup flow and returns authorized headers."""
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "super@test.io", "password": "Passw0rd!123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mfa_setup_required"] is True
    secret = body["setup"]["secret"]
    r2 = client.post(
        "/api/v1/auth/login/2fa/setup",
        json={"login_token": body["login_token"], "secret": secret, "code": _current_totp(secret)},
    )
    assert r2.status_code == 200, r2.text
    return {"Authorization": f"Bearer {r2.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _mfa_reset():
    _reset_super_2fa()
    yield
    _reset_super_2fa()


def test_super_admin_login_requires_mfa_setup(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "super@test.io", "password": "Passw0rd!123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["requires_2fa"] is True
    assert body["mfa_setup_required"] is True
    assert body["login_token"]
    assert body["setup"]["secret"]
    assert body["setup"]["qr_base64"]
    assert "access_token" not in body


def test_super_admin_completes_mfa_setup(client, db):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "super@test.io", "password": "Passw0rd!123"},
    )
    body = r.json()
    secret = body["setup"]["secret"]
    r2 = client.post(
        "/api/v1/auth/login/2fa/setup",
        json={"login_token": body["login_token"], "secret": secret, "code": _current_totp(secret)},
    )
    assert r2.status_code == 200, r2.text
    res = r2.json()
    assert res["access_token"]
    assert res["refresh_token"]
    assert len(res["backup_codes"]) >= 1

    db.expire_all()
    u = db.query(User).filter(User.email == "super@test.io").first()
    assert u.twofa_enabled is True
    assert u.twofa_secret == secret
    assert "[]" not in (u.backup_codes or "")


def test_super_admin_mfa_setup_rejects_bad_code(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "super@test.io", "password": "Passw0rd!123"},
    )
    body = r.json()
    r2 = client.post(
        "/api/v1/auth/login/2fa/setup",
        json={"login_token": body["login_token"], "secret": body["setup"]["secret"], "code": "000000"},
    )
    assert r2.status_code == 401, r2.text
    detail = r2.json()["detail"]
    assert detail["code"] == "INVALID_2FA"


def test_super_admin_second_login_requires_code_not_setup(client):
    _super_headers(client)
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "super@test.io", "password": "Passw0rd!123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["requires_2fa"] is True
    assert not body.get("mfa_setup_required")
    assert "setup" not in body

    db = SessionLocal()
    u = db.query(User).filter(User.email == "super@test.io").first()
    secret = u.twofa_secret
    db.close()
    r2 = client.post(
        "/api/v1/auth/login/2fa",
        json={"login_token": body["login_token"], "code": _current_totp(secret)},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["access_token"]


def test_super_admin_cannot_disable_mfa(client):
    headers = _super_headers(client)
    r = client.post(
        "/api/v1/auth/2fa/disable",
        json={"password": "Passw0rd!123"},
        headers=headers,
    )
    assert r.status_code == 403, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "MFA_REQUIRED"


def test_regular_user_login_unaffected(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "user@test.io", "password": "Passw0rd!123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "requires_2fa" not in body
    assert body["access_token"]
