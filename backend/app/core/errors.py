from __future__ import annotations

import secrets
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        ref: str | None = None,
        details: Any = None,
    ):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.ref = ref or new_error_ref()
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"


class InternalError(AppError):
    status_code = 500
    code = "INTERNAL"


def new_error_ref() -> str:
    return f"CVX-{uuid.uuid4().hex[:6].upper()}"


def error_response(
    message: str, code: str, status: int, ref: str | None = None, details: Any = None
) -> JSONResponse:
    ref = ref or new_error_ref()
    return JSONResponse(
        status_code=status,
        content={
            "detail": {
                "message": message,
                "code": code,
                "ref": ref,
                "details": details,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return error_response(exc.message, exc.code, exc.status_code, exc.ref, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query"))
            details.append({"field": loc, "msg": err.get("msg"), "type": err.get("type")})
        return error_response(
            "Validation failed", "VALIDATION_ERROR", 422, details=details
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return error_response(str(exc.detail), "HTTP_ERROR", exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        from app.core.logging import get_logger

        get_logger("error").exception("unhandled_error", exc=repr(exc))
        return error_response("Something went wrong.", "INTERNAL", 500)
