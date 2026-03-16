"""Mock ESP middleware: rate limiting, latency simulation, and ESP-specific error formatting."""

from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

# ---------------------------------------------------------------------------
# ESP prefix detection
# ---------------------------------------------------------------------------

ESP_PREFIXES = ("/braze", "/sfmc", "/adobe", "/taxi")


def _esp_prefix(path: str) -> str | None:
    """Return the ESP prefix for a given path, or None if not an ESP route."""
    for prefix in ESP_PREFIXES:
        if path.startswith(prefix):
            return prefix.lstrip("/")
    return None


# ---------------------------------------------------------------------------
# 1. Rate limiter middleware (in-memory sliding window)
# ---------------------------------------------------------------------------

_DEFAULT_LIMITS: dict[str, int] = {
    "braze": 100,
    "sfmc": 50,
    "adobe": 30,
    "taxi": 60,
}

# Sliding window storage: esp -> list of timestamps
_request_log: dict[str, list[float]] = {}

WINDOW_SECONDS = 60.0


def _get_rate_limit(esp: str) -> int:
    """Return the per-minute rate limit for an ESP, respecting env overrides."""
    env_key = f"MOCK_ESP_RATE_LIMIT_{esp.upper()}"
    env_val = os.environ.get(env_key)
    if env_val is not None:
        return int(env_val)
    return _DEFAULT_LIMITS.get(esp, 100)


async def rate_limiter_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Sliding-window rate limiter keyed by ESP prefix."""
    esp = _esp_prefix(request.url.path)
    if esp is None:
        return await call_next(request)

    now = time.time()
    cutoff = now - WINDOW_SECONDS

    # Initialise bucket
    if esp not in _request_log:
        _request_log[esp] = []

    # Prune entries older than 60s
    _request_log[esp] = [t for t in _request_log[esp] if t > cutoff]

    limit = _get_rate_limit(esp)
    if len(_request_log[esp]) >= limit:
        retry_after = int(WINDOW_SECONDS - (now - _request_log[esp][0])) + 1
        return esp_error_response(
            request.url.path,
            429,
            "Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    _request_log[esp].append(now)
    return await call_next(request)


# ---------------------------------------------------------------------------
# 2. Latency simulation middleware
# ---------------------------------------------------------------------------


async def latency_simulation_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """Inject random latency before processing the request."""
    min_ms = float(os.environ.get("MOCK_ESP_LATENCY_MIN_MS", "0"))
    max_ms = float(os.environ.get("MOCK_ESP_LATENCY_MAX_MS", "0"))

    if max_ms > 0:
        delay = random.uniform(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)

    return await call_next(request)


# ---------------------------------------------------------------------------
# 3. ESP error formatter
# ---------------------------------------------------------------------------


def esp_error_response(
    path: str,
    status: int,
    message: str,
    *,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Return a JSONResponse formatted in the style of the target ESP."""
    esp = _esp_prefix(path)

    if esp == "braze":
        body: dict[str, Any] = {"errors": [{"message": message}]}
    elif esp == "sfmc":
        body = {"errorcode": status, "message": message}
    elif esp == "adobe":
        body = {"error_code": "SVC-100", "title": message, "detail": message}
    elif esp == "taxi":
        body = {"error": message, "code": f"TAXI-{status}"}
    else:
        body = {"error": message}

    return JSONResponse(status_code=status, content=body, headers=headers)


# ---------------------------------------------------------------------------
# 4. Validation error handler
# ---------------------------------------------------------------------------


async def esp_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format FastAPI validation errors in ESP-specific style."""
    details = exc.errors()
    messages = "; ".join(
        f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg', '')}" for e in details
    )
    return esp_error_response(request.url.path, 422, messages)
