import threading

import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.errors import AppError
from app.models.cvx import CvxLedger
from app.models.user import User
from app.services import cvx_service
from tests.conftest import user_id


def _get_user(email):
    db = SessionLocal()
    try:
        return db, db.query(User).filter(User.email == email).first()
    except Exception:
        db.close()
        raise


def _reset_user(email="user@test.io"):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        db.query(CvxLedger).filter(CvxLedger.user_id == u.id).delete()
        u.cvx_balance = 0.0
        u.cvx_lifetime_earned = 0.0
        u.cvx_lifetime_spent = 0.0
        db.commit()
    finally:
        db.close()


def test_credit_and_ledger():
    _reset_user()
    db, user = _get_user("user@test.io")
    try:
        start = user.cvx_balance or 0
        ledger = cvx_service.credit(
            db, user, 500.0, "CREDIT", "test credit", created_by="test"
        )
        assert ledger.balance_after == start + 500.0
        assert user.cvx_balance == start + 500.0
        entries = db.query(CvxLedger).filter(CvxLedger.user_id == user.id).all()
        assert len(entries) == 1
        assert entries[0].transaction_type == "CREDIT"
        assert entries[0].amount == 500.0
    finally:
        db.close()


def test_debit_insufficient_balance():
    _reset_user()
    db, user = _get_user("user@test.io")
    try:
        user.cvx_balance = 100.0
        db.commit()
        try:
            cvx_service.debit(db, user, 200.0, "SERVER_PURCHASE", "too much")
            assert False, "expected AppError"
        except AppError as exc:
            assert exc.code == "INSUFFICIENT_CVX"
    finally:
        db.close()


def test_debit_negative_blocked():
    _reset_user()
    db, user = _get_user("user@test.io")
    try:
        user.cvx_balance = 1000.0
        db.commit()
        try:
            cvx_service.debit(db, user, -50.0, "SERVER_PURCHASE", "negative")
            assert False, "expected AppError"
        except AppError as exc:
            assert exc.code == "INVALID_AMOUNT"
    finally:
        db.close()


def test_daily_limit_enforced():
    _reset_user()
    db, user = _get_user("user@test.io")
    try:
        # seed a day's worth already earned
        cvx_service.credit(
            db, user, 5000.0, "CREDIT", "fill daily", check_limits=False,
            created_by="test",
        )
        try:
            cvx_service.credit(
                db, user, 1.0, "CREDIT", "over daily", created_by="test"
            )
            assert False, "expected DAILY_LIMIT"
        except AppError as exc:
            assert exc.code == "DAILY_LIMIT"
    finally:
        db.close()


@pytest.mark.skipif(
    engine.dialect.name == "sqlite",
    reason="SELECT ... FOR UPDATE is a Postgres-only guard; SQLite serializes writes.",
)
def test_concurrent_debit_no_negative_balance():
    """Two threads debiting more than the balance must not both succeed."""
    _reset_user()
    db2 = SessionLocal()
    u2 = db2.query(User).filter(User.email == "user@test.io").first()
    u2.cvx_balance = 300.0
    db2.commit()
    db2.close()

    results = []

    def try_debit():
        try:
            dbs = SessionLocal()
            us = dbs.query(User).filter(User.email == "user@test.io").first()
            cvx_service.debit(dbs, us, 200.0, "SERVER_PURCHASE", "race", created_by="test")
            results.append("ok")
            dbs.close()
        except AppError:
            results.append("blocked")
            dbs.close()

    t1 = threading.Thread(target=try_debit)
    t2 = threading.Thread(target=try_debit)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # exactly one should succeed on a shared balance of 300 vs 200+200
    assert results.count("ok") == 1, f"expected exactly one success, got {results}"

    db3 = SessionLocal()
    u3 = db3.query(User).filter(User.email == "user@test.io").first()
    assert u3.cvx_balance == 100.0
    db3.close()


def test_ledger_balance_after_is_monotonic():
    import time

    _reset_user()
    db, user = _get_user("user@test.io")
    try:
        user.cvx_balance = 0
        db.commit()
        cvx_service.credit(db, user, 100.0, "CREDIT", "a", created_by="test")
        time.sleep(0.05)
        cvx_service.credit(db, user, 50.0, "BONUS", "b", created_by="test")
        time.sleep(0.05)
        cvx_service.debit(db, user, 30.0, "SERVER_PURCHASE", "c", created_by="test")
        rows = (
            db.query(CvxLedger)
            .filter(CvxLedger.user_id == user.id)
            .order_by(CvxLedger.created_at.asc())
            .all()
        )
        running = 0.0
        for r in rows:
            running += r.amount
            assert abs(r.balance_after - running) < 1e-6
    finally:
        db.close()
