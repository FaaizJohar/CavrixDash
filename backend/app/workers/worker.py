from __future__ import annotations

import time

from app.core.database import SessionLocal, check_db_ready
from app.core.logging import get_logger, setup_logging

setup_logging()
log = get_logger("worker")


def _tick() -> None:
    from app.services import worker_service

    db = SessionLocal()
    try:
        worker_service.expire_servers(db)
        worker_service.sync_nodes(db)
        worker_service.expire_tasks(db)
        worker_service.send_announcements(db)
    except Exception as exc:  # pragma: no cover
        log.error("tick_failed", exc=repr(exc))
    finally:
        db.close()


def main() -> None:
    log.info("worker_started")
    while True:
        if check_db_ready():
            _tick()
        time.sleep(30)


if __name__ == "__main__":
    main()
