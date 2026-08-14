from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply secure response headers.

    Headers are conditionally applied so local development over plain HTTP
    still works: HSTS is only emitted for HTTPS requests, and CSP forbid
    frames/eval hardening is skipped when app_debug is enabled to keep the
    Vite dev server functional.
    """

    def __init__(self, app, *, is_prod: bool = False):
        super().__init__(app)
        self.is_prod = is_prod

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if self.is_prod and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        if not request.url.path.startswith("/ws"):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; font-src 'self' data:; connect-src 'self' ws: wss:; "
                "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            )
        return response