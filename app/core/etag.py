"""ETag middleware for JSON GET responses."""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


class ETagMiddleware(BaseHTTPMiddleware):
    """Generate ETags for GET JSON responses; return 304 when unchanged."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        # Only ETag GET requests with JSON responses
        if request.method != "GET":
            return response

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        # Read response body — body_iterator yields bytes or str chunks
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
            raw = cast("bytes | str", chunk)
            chunks.append(raw if isinstance(raw, bytes) else raw.encode())
        body = b"".join(chunks)

        etag = f'"{hashlib.md5(body).hexdigest()}"'  # noqa: S324

        # Check If-None-Match
        if_none_match = request.headers.get("if-none-match")
        if if_none_match == etag:
            return Response(
                status_code=304,
                headers={"ETag": etag, "Cache-Control": "no-cache, must-revalidate"},
            )

        # Return original response with ETag headers
        headers = dict(response.headers)
        headers["ETag"] = etag
        headers["Cache-Control"] = "no-cache, must-revalidate"

        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
