from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings as app_settings
from app.models.offer import Offer
from app.models.provider import Provider
from app.services import provider_service
from app.services.provider_service import is_sync_due, sync_enabled_providers

_OFFER = {
    "external_id": "fake-offer-1",
    "title": "Fake Offer",
    "description": "d",
    "category": "games",
    "icon_url": "",
    "reward": 100,
    "payout": 0.10,
    "estimated_time": 5,
    "countries": ["IN"],
    "devices": ["android"],
    "requirements": "r",
    "conversion_event": "action",
    "click_url": "https://example.test/click",
    "landing_url": "",
    "status": "active",
    "meta": {},
}


class _FakeAdapter:
    code = "fake"
    name = "Fake"
    kind = "offerwall"
    fail = False

    def __init__(self) -> None:
        self.fail = False

    def test_connection(self, credentials):
        return {"ok": not self.fail}

    def sync_offers(self, credentials):
        if self.fail:
            raise RuntimeError("upstream down")
        return [dict(_OFFER)]


@pytest.fixture
def fake_provider(db):
    for p in db.query(Provider).all():
        db.query(Offer).filter(Offer.provider_id == p.id).delete(synchronize_session=False)
        db.delete(p)
    db.commit()
    p = Provider(code="fake", name="Fake", kind="offerwall", enabled=True)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture
def fake_adapter(monkeypatch):
    adapter = _FakeAdapter()

    def _stub(code: str):
        if code == "fake":
            return adapter
        return None

    monkeypatch.setattr(provider_service, "get_adapter", _stub)
    return adapter


def test_healthy_provider_syncs_offers(db, fake_provider, fake_adapter):
    summary = sync_enabled_providers(db)
    assert summary["synced"] == ["fake"]
    assert summary["offers"] == 1
    assert summary["pending_backoff"] == 0
    assert summary["failed"] == []
    db.refresh(fake_provider)
    assert fake_provider.sync_error_count == 0
    assert fake_provider.last_synced_at
    assert fake_provider.status == "connected"
    assert db.query(Offer).filter(Offer.provider_id == fake_provider.id).count() == 1


def test_failing_provider_increments_error_count_and_backs_off(db, fake_provider, fake_adapter):
    fake_adapter.fail = True
    summary = sync_enabled_providers(db)
    assert [f["code"] for f in summary["failed"]] == ["fake"]
    db.refresh(fake_provider)
    assert fake_provider.sync_error_count == 1
    assert fake_provider.status == "error"
    assert fake_provider.last_attempt_at

    # Second run is immediately suppressed by exponential backoff.
    db.expire_all()
    summary = sync_enabled_providers(db)
    assert summary["failed"] == []
    assert summary["pending_backoff"] == 1


def test_backoff_cleared_after_success(db, fake_provider, fake_adapter):
    fake_adapter.fail = True
    sync_enabled_providers(db)
    db.refresh(fake_provider)
    fake_provider.sync_error_count = 3
    # Force due by backdating the attempt beyond the current backoff window.
    fake_provider.last_attempt_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    db.commit()

    fake_adapter.fail = False
    db.expire_all()
    summary = sync_enabled_providers(db)
    assert summary["synced"] == ["fake"]
    db.refresh(fake_provider)
    assert fake_provider.sync_error_count == 0
    assert fake_provider.last_error == ""


def test_is_sync_due_backoff_math(db, fake_provider):
    now = datetime.now(timezone.utc)
    fake_provider.last_attempt_at = now.isoformat()
    fake_provider.sync_error_count = 0
    assert is_sync_due(db, fake_provider) is False

    fake_provider.last_attempt_at = (now - timedelta(minutes=app_settings.provider_sync_interval_minutes + 1)).isoformat()
    assert is_sync_due(db, fake_provider) is True

    # Consecutive failures escalate: delay = base * 2^(n-1), capped.
    fake_provider.last_attempt_at = now.isoformat()
    fake_provider.sync_error_count = 1
    assert is_sync_due(db, fake_provider) is False
    fake_provider.last_attempt_at = (now - timedelta(seconds=app_settings.provider_sync_error_base_seconds + 1)).isoformat()
    assert is_sync_due(db, fake_provider) is True

    fake_provider.sync_error_count = 10
    fake_provider.last_attempt_at = now.isoformat()
    cap = app_settings.provider_sync_max_backoff_minutes * 60
    fake_provider.last_attempt_at = (now - timedelta(seconds=cap + 1)).isoformat()
    assert is_sync_due(db, fake_provider) is True
    fake_provider.last_attempt_at = (now - timedelta(seconds=cap - 1)).isoformat()
    assert is_sync_due(db, fake_provider) is False
