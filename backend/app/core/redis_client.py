from __future__ import annotations

import redis

from app.core.config import settings

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2,
        )
    return _redis_client


def ping_redis() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
