from app.core.database import SessionLocal
from app.models.user import Role, User
from tests.conftest import auth_headers, step_up_headers, user_id


def test_finance_admin_can_access_finance_endpoints(client):
    h = auth_headers(client, "finance@test.io")
    for path in ("/api/v1/admin/revenue", "/api/v1/admin/overview", "/api/v1/admin/conversions", "/api/v1/admin/cvx/settings", "/api/v1/admin/offers"):
        r = client.get(path, headers=h)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text}"


def test_finance_admin_blocked_from_infra_and_staff(client):
    h = auth_headers(client, "finance@test.io")
    for path in ("/api/v1/admin/nodes", "/api/v1/admin/plans", "/api/v1/admin/servers", "/api/v1/admin/users", "/api/v1/admin/audit"):
        r = client.get(path, headers=h)
        assert r.status_code == 403, f"{path}: {r.status_code} {r.text}"

    r = client.patch("/api/v1/admin/plans/nonexistent", json={"status": "paused"}, headers=h)
    assert r.status_code == 403, r.text


def test_infra_admin_can_access_infra_endpoints(client):
    h = auth_headers(client, "infra@test.io")
    for path in ("/api/v1/admin/overview", "/api/v1/admin/plans", "/api/v1/admin/regions", "/api/v1/admin/nodes", "/api/v1/admin/templates", "/api/v1/admin/upgrade-prices", "/api/v1/admin/servers"):
        r = client.get(path, headers=h)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text}"

    r = client.patch("/api/v1/admin/plans/nonexistent", json={"status": "paused"}, headers=h)
    assert r.status_code == 404, r.text  # authz passed; plan lookup failed


def test_infra_admin_blocked_from_finance(client):
    h = auth_headers(client, "infra@test.io")
    for path in ("/api/v1/admin/revenue", "/api/v1/admin/conversions", "/api/v1/admin/cvx/settings", "/api/v1/admin/users"):
        r = client.get(path, headers=h)
        assert r.status_code == 403, f"{path}: {r.status_code} {r.text}"


def test_scoped_admin_login_requires_mfa(client):
    with SessionLocal() as db:
        u = db.query(User).filter(User.email == "finance@test.io").first()
        u.twofa_enabled = False
        u.twofa_secret = ""
        u.backup_codes = "[]"
        db.commit()
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "finance@test.io", "password": "Passw0rd!123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["requires_2fa"] is True
    assert body["mfa_setup_required"] is True


def test_super_admin_can_assign_scoped_roles(client):
    h = step_up_headers(client, "super@test.io")
    with SessionLocal() as db:
        target = user_id(db, "user@test.io")
    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"roles": ["user", "finance_admin"]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert "finance_admin" in r.json()["roles"]
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == target).first()
        user_role = db.query(Role).filter(Role.name == "user").first()
        u.roles = [user_role]
        u.twofa_enabled = False
        u.twofa_secret = ""
        u.backup_codes = "[]"
        db.commit()


def test_non_super_admin_cannot_assign_scoped_roles(client):
    h = auth_headers(client, "admin@test.io")
    with SessionLocal() as db:
        target = user_id(db, "user@test.io")
    r = client.patch(
        f"/api/v1/admin/users/{target}",
        json={"roles": ["infra_admin"]},
        headers=h,
    )
    assert r.status_code == 403, r.text
