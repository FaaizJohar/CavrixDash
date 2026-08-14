"""Redis client wrapper. Gracefully degrades to an in-memory fallback when
Redis is unavailable so the app remains runnable in dev without Redis.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Callable, Optional

import redis as redis_lib

from app.core.config import settings
from app.core.logging import logger

_pool: Optional[redis_lib.Redis] = None
_lock = threading.Lock()
_unavailable = False


class MemoryStore:
    """Thread-safe in-memory fallback implementing the tiny subset we use."""

    def __init__(self):
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if expires is not None and expires < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ex: Optional[int] = None):
        with self._lock:
            expires = (time.time() + ex) if ex else None
            self._data[key] = (expires, value)

    def incr(self, key: str, amount: int = 1) -> int:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                self._data[key] = (None, amount)
                return amount
            self._data[key] = (item[0], (item[1] or 0) + amount)
            return self._data[key][1]

    def expire(self, key: str, seconds: int):
        with self._lock:
            item = self._data.get(key)
            if item:
                self._data[key] = (time.time() + seconds, item[1])

    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)


_memory = MemoryStore()


def _get_client() -> redis_lib.Redis:
    global _pool, _unavailable
    if _pool is not None:
        return _pool
    with _lock:
        if _pool is not None:
            return _pool
        if _unavailable or not settings.REDIS_URL:
            return None  # type: ignore[return-value]
        try:
            client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
            client.ping()
            _pool = client
            logger.info("redis_connected")
            return client
        except Exception:
            _unavailable = True
            logger.warning("redis_unavailable_using_memory")
            return None  # type: ignore[return-value]


def _store() -> Any:
    return _get_client() or _memory


def cache_get(key: str) -> Optional[Any]:
    val = _store().get(key)
    if val is None:
        return None
    try:
        return json.loads(val) if isinstance(val, str) else val
    except Exception:
        return val


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    try:
        _store().set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:
        logger.warning("cache_set_failed", error=str(exc))


def cache_delete(pattern: str) -> None:
    store = _store()
    try:
        if isinstance(store, redis_lib.Redis):
            for key in store.scan_iter(match=pattern):
                store.delete(key)
        else:
            with _memory._lock:
                keys = [k for k in _memory._data if k.startswith(pattern.replace("*", ""))]
                for k in keys:
                    _memory._data.pop(k, None)
    except Exception:
        pass


def rate_limit_key(scope: str, identifier: str) -> str:
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:24]
    return f"rl:{scope}:{digest}"


def incr_counter(key: str, ttl: Optional[int] = None) -> int:
    store = _store()
    try:
        value = store.incr(key)
        if ttl and value == 1:
            store.expire(key, ttl)
        return int(value)
    except Exception as exc:
        logger.warning("incr_failed", error=str(exc))
        return 0


def pubsub_channel() -> Optional[Any]:
    client = _get_client()
    if isinstance(client, redis_lib.Redis):
        return client.pubsub()
    return None
