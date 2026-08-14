from __future__ import annotations

import time
from typing import Any

from app.core.errors import RateLimitedError
from app.core.redis_client import get_redis

_FIXED_WINDOW = 60


def _key(kind: str, ident: str) -> str:
    return f"rl:{kind}:{ident}:{int(time.time()) // _FIXED_WINDOW}"


def hit(kind: str, ident: str, limit: int) -> None:
    """Increment fixed-window counter; raise when over limit."""
    key = _key(kind, ident)
    try:
        r = get_redis()
        cur = r.incr(key)
        if cur == 1:
            r.expire(key, _FIXED_WINDOW + 1)
        if cur > limit:
            raise RateLimitedError("Too many requests. Please slow down.", code="RATE_LIMITED")
    except RateLimitedError:
        raise
    except Exception:
        # Redis down: fail open for auth flows is risky, but we still allow general flow.
        pass


def check(kind: str, ident: str, limit: int) -> bool:
    try:
        return int(get_redis().get(_key(kind, ident)) or 0) < limit
    except Exception:
        return True


def set_ttl(key: str, value: Any, ttl: int) -> None:
    try:
        get_redis().setex(key, ttl, value)
    except Exception:
        pass


def get(key: str) -> Any:
    try:
        return get_redis().get(key)
    except Exception:
        return None


def incr(key: str, ttl: int = 86400) -> int:
    try:
        r = get_redis()
        v = r.incr(key)
        if v == 1:
            r.expire(key, ttl)
        return int(v)
    except Exception:
        return 0
