import pytest

from app.core.database import SessionLocal
from app.core.security import _totp_at, generate_totp_secret
from app.models.server import UserServer
from app.models.user import User
from tests.conftest import auth_headers, step_up_headers, user_id

import time


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


def _enable_super_2fa() -> str:
    secret = generate_totp_secret()
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == "super@test.io").first()
        u.twofa_enabled = True
        u.twofa_secret = secret
        u.backup_codes = "[]"
        db.commit()
    finally:
        db.close()
    return secret


@pytest.fixture(autouse=True)
def _reset():
    _reset_super_2fa()
    yield


def test_stepup_rejects_wrong_password(client):
    h = auth_headers(client, "admin@test.io")
    r = client.post("/api/v1/auth/step-up", json={"password": "wrong-password"}, headers=h)
    assert r.status_code == 401, r.text
    assert r.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_stepup_returns_token_for_admin(client):
    h = auth_headers(client, "admin@test.io")
    r = client.post("/api/v1/auth/step-up", json={"password": "Passw0rd!123"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["step_up_token"]
    assert r.json()["expires_in"] == 300


def test_stepup_super_admin_requires_totp(client):
    secret = _enable_super_2fa()
    h = auth_headers(client, "super@test.io")
    r = client.post("/api/v1/auth/step-up", json={"password": "Passw0rd!123"}, headers=h)
    assert r.status_code == 401, r.text
    assert r.json()["detail"]["code"] == "INVALID_2FA"

    code = _totp_at(secret, int(time.time() // 30))
    r2 = client.post(
        "/api/v1/auth/step-up",
        json={"password": "Passw0rd!123", "totp_code": code},
        headers=h,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["step_up_token"]


def test_cvx_adjustment_requires_stepup(client):
    h = auth_headers(client, "admin@test.io")
    with SessionLocal() as db:
        target = user_id(db, "user@test.io")

    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"cvx_adjustment": 100, "cvx_adjustment_reason": "test"},
        headers=h,
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "STEP_UP_REQUIRED"

    h2 = step_up_headers(client, "admin@test.io")
    with SessionLocal() as db:
        start = (db.query(User).filter(User.id == target).first().cvx_balance) or 0.0
    r2 = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"cvx_adjustment": 100, "cvx_adjustment_reason": "test"},
        headers=h2,
    )
    assert r2.status_code == 200, r2.text
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == target).first()
        assert u.cvx_balance == start + 100.0
        u.cvx_balance = 0.0
        db.commit()


def test_status_change_does_not_require_stepup(client):
    h = auth_headers(client, "admin@test.io")
    with SessionLocal() as db:
        target = user_id(db, "user@test.io")
    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"status": "suspended"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == target).first()
        u.status = "active"
        db.commit()


def test_role_change_requires_stepup(client):
    h = auth_headers(client, "super@test.io")
    with SessionLocal() as db:
        target = user_id(db, "user@test.io")
    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"roles": ["moderator"]},
        headers=h,
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "STEP_UP_REQUIRED"


def test_secrets_reveal_requires_stepup(client):
    h = auth_headers(client, "super@test.io")
    r = client.get("/api/v1/admin/secrets", headers=h)
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "STEP_UP_REQUIRED"

    h2 = step_up_headers(client, "super@test.io")
    r2 = client.get("/api/v1/admin/secrets", headers=h2)
    assert r2.status_code == 200, r2.text


def test_server_destroy_requires_stepup(client):
    h = auth_headers(client, "super@test.io")
    r = client.delete("/api/v1/admin/servers/nonexistent", headers=h)
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "STEP_UP_REQUIRED"

    h2 = step_up_headers(client, "super@test.io")
    with SessionLocal() as db:
        u = db.query(User).filter(User.email == "user@test.io").first()
        srv = UserServer(
            user_id=u.id,
            plan_id="plan-test",
            pterodactyl_server_id="ptero-stepup-test",
            name="stepup-test",
        )
        db.add(srv)
        db.commit()
        srv_id = srv.id
    r2 = client.delete(f"/api/v1/admin/servers/{srv_id}", headers=h2)
    # Step-up was accepted (guard would return 403 otherwise); destruction then
    # proceeds to Pterodactyl, which is unconfigured in the test env.
    assert r2.status_code != 403, r2.text
    with SessionLocal() as db:
        db.query(UserServer).filter(UserServer.id == srv_id).delete()
        db.commit()
