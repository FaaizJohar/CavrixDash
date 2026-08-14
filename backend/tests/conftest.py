import os
import tempfile

os.environ["APP_ENV"] = "test"
os.environ["DB_AUTO_CREATE"] = "false"
os.environ["MOCK_PROVIDER_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdefghijklmnopqrstuvwxyz"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-0123456789abcdef"

# Keep the test DB off the (often full) system temp drive: place it next to the
# tests dir on the project drive instead.
_db_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".test_cavrix.db"
)
if os.path.exists(_db_path):
    os.remove(_db_path)
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.user import Role, User
from app.services.user_service import _referral_code


@pytest.fixture(scope="session", autouse=True)
def _seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    role_names = ("super_admin", "admin", "support", "moderator", "user", "finance_admin", "infra_admin")
    roles = {n: Role(name=n, description=n, is_system=True) for n in role_names}
    for r in roles.values():
        db.add(r)
    db.flush()

    def make_user(email, rname):
        u = User(
            email=email,
            username=email.split("@")[0],
            display_name=email,
            password_hash=hash_password("Passw0rd!123"),
            email_verified=True,
            status="active",
            referral_code=_referral_code(),
        )
        u.roles.append(roles[rname])
        db.add(u)

    make_user("super@test.io", "super_admin")
    make_user("admin@test.io", "admin")
    make_user("support@test.io", "support")
    make_user("user@test.io", "user")
    make_user("finance@test.io", "finance_admin")
    make_user("infra@test.io", "infra_admin")
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app_import()) as c:
        yield c


def app_import():
    from app.main import app

    return app


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Passw0rd!123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    if body.get("requires_2fa"):
        if body.get("mfa_setup_required"):
            secret = body["setup"]["secret"]
            code = _current_totp(secret)
            r2 = client.post(
                "/api/v1/auth/login/2fa/setup",
                json={"login_token": body["login_token"], "secret": secret, "code": code},
            )
        else:
            from app.core.database import SessionLocal
            from app.models.user import User

            db = SessionLocal()
            u = db.query(User).filter(User.email == email).first()
            secret = u.twofa_secret
            db.close()
            r2 = client.post(
                "/api/v1/auth/login/2fa",
                json={"login_token": body["login_token"], "code": _current_totp(secret)},
            )
        assert r2.status_code == 200, r2.text
        return {"Authorization": f"Bearer {r2.json()['access_token']}"}
    return {"Authorization": f"Bearer {body['access_token']}"}


def _current_totp(secret: str) -> str:
    import time

    from app.core.security import _totp_at

    return _totp_at(secret, int(time.time() // 30))


def step_up_headers(client: TestClient, email: str, password: str = "Passw0rd!123") -> dict[str, str]:
    """Auth headers plus a fresh step-up token for sensitive ops."""
    headers = auth_headers(client, email)
    from app.core.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    u = db.query(User).filter(User.email == email).first()
    twofa_enabled = u.twofa_enabled
    twofa_secret = u.twofa_secret or ""
    db.close()
    body: dict = {"password": password}
    if twofa_enabled:
        body["totp_code"] = _current_totp(twofa_secret)
    r = client.post("/api/v1/auth/step-up", json=body, headers=headers)
    assert r.status_code == 200, r.text
    headers["X-Step-Up-Token"] = r.json()["step_up_token"]
    return headers


def user_id(db_session, email: str) -> str:
    db_session.expire_all()
    u = db_session.query(User).filter(User.email == email).first()
    return u.id


@pytest.fixture
def db():
    db = SessionLocal()
    yield db
    db.close()
