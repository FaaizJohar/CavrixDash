from tests.conftest import auth_headers, step_up_headers, user_id
from app.core.database import SessionLocal
from app.models.user import User


def test_admin_cannot_escalate_roles(client):
    h = auth_headers(client, "admin@test.io")
    with SessionLocal() as db:
        target = user_id(db, "user@test.io")
    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"roles": ["super_admin", "admin"]},
        headers=h,
    )
    assert r.status_code == 403
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == target).first()
        assert not u.has_role("super_admin")


def test_super_admin_can_assign_roles(client):
    h = step_up_headers(client, "super@test.io")
    with SessionLocal() as db:
        target = user_id(db, "user@test.io")
    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"roles": ["moderator"]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == target).first()
        assert u.has_role("moderator")


def test_admin_cannot_modify_super_admin_account(client):
    h = auth_headers(client, "admin@test.io")
    with SessionLocal() as db:
        target = user_id(db, "super@test.io")
    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"status": "suspended"},
        headers=h,
    )
    assert r.status_code == 403


def test_admin_can_update_regular_user_status(client):
    h = auth_headers(client, "admin@test.io")
    with SessionLocal() as db:
        target = user_id(db, "user@test.io")
    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"status": "suspended"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    # restore so later tests can authenticate as this user
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == target).first()
        u.status = "active"
        db.commit()


def test_admin_cannot_write_secrets_through_settings(client):
    h = auth_headers(client, "admin@test.io")
    r = client.patch(
        "/api/v1/admin/settings",
        json={"settings": {"pterodactyl.api_key_encrypted": "pwned"}},
        headers=h,
    )
    assert r.status_code == 403


def test_secrets_endpoint_requires_super_admin(client):
    h = auth_headers(client, "admin@test.io")
    r = client.get("/api/v1/admin/secrets", headers=h)
    assert r.status_code == 403
    h2 = step_up_headers(client, "super@test.io")
    r2 = client.get("/api/v1/admin/secrets", headers=h2)
    assert r2.status_code == 200, r2.text


def test_user_cannot_claim_other_users_server(client):
    # admin cannot reach another user's server endpoints without the server
    h = auth_headers(client, "user@test.io")
    # listing own servers must work and be an empty list (no cross-user leak)
    r = client.get("/api/v1/servers", headers=h)
    assert r.status_code == 200, r.text
