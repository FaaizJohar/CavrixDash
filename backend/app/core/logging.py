from __future__ import annotations

import hashlib
import logging
import os
import uuid
from typing import Callable

import structlog
from structlog.processors import JSONRenderer, TimeStamper
from structlog.stdlib import add_log_level

from app.core.config import settings

_RENDER_JSON = settings.log_format.lower() == "json"


def _add_request_context(logger, method, event_dict):
    ctx = getattr(logging_context, "current", None)
    if ctx:
        event_dict["request_id"] = ctx.get("request_id")
        event_dict["user_id"] = ctx.get("user_id")
        event_dict["ip"] = ctx.get("ip")
    return event_dict


class logging_context:
    current: dict | None = None


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    processors: list[Callable] = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        TimeStamper(fmt="iso"),
        _add_request_context,
    ]
    if _RENDER_JSON:
        processors.append(JSONRenderer(ensure_ascii=False))
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(_ConsoleFormatter())
    root.addHandler(handler)


class _ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        return f"{ts} {record.levelname} {record.name}: {record.getMessage()}"


def get_logger(name: str = "cavrix"):
    return structlog.get_logger(name)


def new_request_id() -> str:
    return uuid.uuid4().hex[:8].upper()
