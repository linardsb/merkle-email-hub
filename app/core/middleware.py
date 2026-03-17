"""Request/response middleware for FastAPI application.

Provides:
- Body size limiting with configurable upload paths
- Request logging with correlation IDs
- CORS middleware setup
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.logging import get_logger, get_request_id, set_request_id

logger = get_logger(__name__)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that rejects request bodies exceeding a size limit.

    Returns HTTP 413 (Content Too Large) for requests exceeding the limit.
    Configurable upload paths allow larger payloads for file-based endpoints.
    """

    # Paths that allow larger uploads (50MB)
    UPLOAD_PATHS: tuple[str, ...] = ("/api/v1/knowledge", "/api/v1/ai/voice", "/mcp")

    def __init__(self, app: ASGIApp, max_body_size: int = 102_400) -> None:
        super().__init__(app)
        self._max_body_size = max_body_size

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in self.UPLOAD_PATHS):
            max_size = 52_428_800  # 50MB for file uploads
        else:
            max_size = self._max_body_size

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid Content-Length header"},
                )
            if length > max_size:
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request body too large", "max_bytes": max_size},
                )
        elif content_length is None and not any(path.startswith(p) for p in self.UPLOAD_PATHS):
            if request.method in ("POST", "PUT", "PATCH"):
                return JSONResponse(
                    status_code=411,
                    content={"detail": "Content-Length required"},
                )
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with correlation ID."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID")
        set_request_id(request_id)

        start_time = time.time()
        logger.info(
            "request.http_received",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            logger.info(
                "request.http_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,  # pyright: ignore[reportUnknownMemberType]
                duration_seconds=round(duration, 3),
            )

            response.headers["X-Request-ID"] = get_request_id()  # pyright: ignore[reportUnknownMemberType]
            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "request.http_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_seconds=round(duration, 3),
                exc_info=True,
            )
            raise


def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the application."""
    settings = get_settings()

    app.add_middleware(BodySizeLimitMiddleware, max_body_size=102_400)
    app.add_middleware(RequestLoggingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "Accept",
            "Accept-Language",
        ],
    )
