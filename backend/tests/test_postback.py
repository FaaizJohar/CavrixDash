import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.cvx import CvxLedger
from app.models.offer import Offer
from app.models.provider import Provider
from app.models.tracking import Conversion, TaskClick
from app.models.user import User
from tests.conftest import user_id


@pytest.fixture(autouse=True)
def _mock_provider_flag():
    settings.mock_provider_enabled = True
    yield
    settings.mock_provider_enabled = False


def _seed_conversion(db, provider_code: str, click_id: str, conversion_id: str) -> tuple[str, str]:
    provider = db.query(Provider).filter(Provider.code == provider_code).first()
    if not provider:
        provider = Provider(code=provider_code, name="Mock", kind="mock", enabled=True)
        db.add(provider)
        db.flush()
    offer = db.query(Offer).filter(Offer.provider_id == provider.id).first()
    if not offer:
        offer = Offer(
            provider_id=provider.id,
            external_id="offer-1",
            title="Test Offer",
            reward=100.0,
            payout=1.0,
        )
        db.add(offer)
        db.flush()
    uid = user_id(db, "user@test.io")
    if not db.query(TaskClick).filter(TaskClick.click_id == click_id).first():
        click = TaskClick(
            click_id=click_id,
            user_id=uid,
            offer_id=offer.id,
            provider_id=provider.id,
            session_id="sess-replay",
            ip="10.0.0.1",
            user_agent="pytest",
            device_id="dev-replay",
            reward_offered=offer.effective_reward,
        )
        db.add(click)
        db.flush()
    return uid, offer.id


def _reset_user(db, uid: str) -> None:
    db.query(CvxLedger).filter(CvxLedger.user_id == uid).delete()
    u = db.query(User).filter(User.id == uid).first()
    u.cvx_balance = 0.0
    u.cvx_lifetime_earned = 0.0
    u.cvx_lifetime_spent = 0.0
    u.conversions_approved = 0
    u.tasks_completed = 0
    db.commit()


def _postback(client, conversion_id: str):
    return client.post(
        "/api/v1/postbacks/mock",
        json={
            "sub1": "click-replay-1",
            "conversion_id": conversion_id,
            "status": "approved",
            "payout": 1.0,
            "txn_id": "tx-replay-1",
        },
    )


def test_postback_replay_is_duplicate_and_credited_once(client, db):
    uid, _ = _seed_conversion(db, "mock", "click-replay-1", "conv-replay-1")
    _reset_user(db, uid)
    _postback(client, "conv-replay-1")
    db.expire_all()
    user = db.query(User).filter(User.id == uid).first()
    assert user.cvx_balance == 100.0

    db.expire_all()
    provider = db.query(Provider).filter(Provider.code == "mock").first()
    first = (
        db.query(Conversion)
        .filter(
            Conversion.provider_id == provider.id,
            Conversion.conversion_id == "conv-replay-1",
        )
        .first()
    )
    assert first.status == "approved"

    r = _postback(client, "conv-replay-1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "duplicate"
    assert body["conversion_status"] == "approved"

    db.expire_all()
    user = db.query(User).filter(User.id == uid).first()
    assert user.cvx_balance == 100.0, "replay must not double-credit"
    count = (
        db.query(Conversion)
        .filter(
            Conversion.provider_id == provider.id,
            Conversion.conversion_id == "conv-replay-1",
        )
        .count()
    )
    assert count == 1


def test_db_rejects_duplicate_provider_conversion(db):
    provider = db.query(Provider).filter(Provider.code == "mock").first()
    if not provider:
        provider = Provider(code="mock", name="Mock", kind="mock", enabled=True)
        db.add(provider)
        db.flush()
    uid = user_id(db, "user@test.io")

    def make():
        return Conversion(
            click_id="click-db-1",
            user_id=uid,
            offer_id="offer-db-1",
            provider_id=provider.id,
            conversion_id="conv-db-1",
            external_tx_id="tx-db-1",
            ip="",
            device_id="dev-db-1",
            status="pending",
        )

    db.add(make())
    db.flush()
    db.add(make())
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
