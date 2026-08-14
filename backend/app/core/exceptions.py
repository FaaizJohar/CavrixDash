"""Typed application errors + error handler.

Errors raised here map to clean client-facing messages with a reference code.
Raw backend errors are never surfaced to the user.
"""
from __future__ import annotations

import secrets
import traceback
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from structlog.contextvars import bind_contextvars
from sqlalchemy.exc import IntegrityError

from app.core.logging import logger


class AppError(Exception):
    """Base application error with an HTTP status + reference code."""

    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message: str = "Something went wrong.", reference: Optional[str] = None):
        self.message = message
        self.reference = reference or f"CVX-{secrets.token_hex(3).upper()}"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMITED"


class MaintenanceModeError(AppError):
    status_code = 503
    code = "MAINTENANCE"


class ValidationAppError(AppError):
    status_code = 422
    code = "VALIDATION"


def error_payload(status: int, message: str, code: str, reference: str) -> dict:
    return {"error": {"message": message, "code": code, "reference": reference}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        bind_contextvars(error_code=exc.code, reference=exc.reference, path=request.url.path)
        logger.warning("app_error", message=exc.message, status=exc.status_code, code=exc.code)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.status_code, exc.message, exc.code, exc.reference),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        ref = f"CVX-{secrets.token_hex(3).upper()}"
        detail = str(exc)
        logger.warning("validation_error", reference=ref, path=request.url.path, detail=detail)
        return JSONResponse(
            status_code=422,
            content=error_payload(422, "Invalid request data.", "VALIDATION", ref),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        ref = f"CVX-{secrets.token_hex(3).upper()}"
        logger.error("integrity_error", reference=ref, path=request.url.path, error=exc.orig)
        return JSONResponse(
            status_code=409,
            content=error_payload(409, "That operation conflicts with existing data.", "CONFLICT", ref),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        ref = f"CVX-{secrets.token_hex(3).upper()}"
        bind_contextvars(reference=ref, path=request.url.path)
        logger.error("unhandled_error", reference=ref, exc_info=True, trace=traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content=error_payload(500, "Something went wrong.", "INTERNAL", ref),
        )
