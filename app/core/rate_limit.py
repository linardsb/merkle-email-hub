"""Rate limiting configuration using slowapi.

Uses Redis as the storage backend when available so rate limits are enforced
across all workers. Falls back to in-memory storage for development/test.
"""

from slowapi import Limiter  # pyright: ignore[reportMissingTypeStubs]
from slowapi.util import get_remote_address  # pyright: ignore[reportMissingTypeStubs]
from starlette.requests import Request

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request for rate limiting.

    Uses X-Real-IP header (set by nginx, not client-spoofable) if present,
    falls back to direct client address.
    """
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return get_remote_address(request)


def _get_storage_uri() -> str | None:
    """Return Redis URI for rate limit storage, or None for in-memory fallback."""
    import redis

    settings = get_settings()
    try:
        client = redis.Redis.from_url(settings.redis.url, socket_connect_timeout=1)  # pyright: ignore[reportUnknownMemberType]
        client.ping()  # pyright: ignore[reportUnknownMemberType]
        client.close()
        return settings.redis.url
    except Exception as e:
        logger.warning(
            "rate_limit.redis_unavailable",
            error=str(e),
            error_type=type(e).__name__,
            detail="Falling back to in-memory storage (rate limits per-worker only)",
        )
        return None


_storage_uri = _get_storage_uri()
limiter = Limiter(
    key_func=_get_client_ip,
    storage_uri=_storage_uri,
)
