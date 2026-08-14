from app.core.errors import RateLimitedError
from tests.conftest import auth_headers


def _enforcing_hit(calls: dict):
    def hit(kind: str, ident: str, limit: int) -> None:
        key = (kind, ident)
        calls[key] = calls.get(key, 0) + 1
        if calls[key] > limit:
            raise RateLimitedError("Too many requests. Please slow down.", code="RATE_LIMITED")

    return hit


def test_server_create_rate_limited(client, monkeypatch):
    calls: dict = {}
    monkeypatch.setattr("app.api.routers.servers.rate_hit", _enforcing_hit(calls))
    h = auth_headers(client, "user@test.io")
    payload = {"plan_id": "plan-x", "region": "us", "server_name": "rate-test"}

    for _ in range(3):
        client.post("/api/v1/servers", json=payload, headers=h)

    r = client.post("/api/v1/servers", json=payload, headers=h)
    assert r.status_code == 429, r.text
    assert r.json()["detail"]["code"] == "RATE_LIMITED"


def test_server_action_rate_limited(client, monkeypatch):
    calls: dict = {}
    monkeypatch.setattr("app.api.routers.servers.rate_hit", _enforcing_hit(calls))
    h = auth_headers(client, "user@test.io")

    for _ in range(30):
        client.post("/api/v1/servers/nonexistent/action", json={"action": "restart"}, headers=h)

    r = client.post("/api/v1/servers/nonexistent/action", json={"action": "restart"}, headers=h)
    assert r.status_code == 429, r.text
    assert r.json()["detail"]["code"] == "RATE_LIMITED"


def test_server_claim_counts_failed_attempts(client, monkeypatch):
    """Rate hit runs before validation/claim, so invalid attempts also consume quota."""
    calls: dict = {}
    monkeypatch.setattr("app.api.routers.servers.rate_hit", _enforcing_hit(calls))
    h = auth_headers(client, "user@test.io")
    payload = {"plan_id": "plan-x", "region": "us", "server_name": "rate-test"}

    for _ in range(3):
        client.post("/api/v1/servers", json=payload, headers=h)

    r = client.post("/api/v1/servers", json=payload, headers=h)
    assert r.status_code == 429, r.text
