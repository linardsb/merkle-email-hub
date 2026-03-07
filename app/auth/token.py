"""JWT token creation and validation utilities."""

import datetime
import uuid
from typing import Any

import jwt
from jwt import InvalidTokenError
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Pinned algorithm — never read from config to prevent algorithm confusion attacks.
# HS256 (HMAC-SHA256) with a strong secret is sufficient for single-service JWT.
_JWT_ALGORITHM: str = "HS256"


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: int  # user_id
    role: str
    exp: datetime.datetime
    type: str  # "access" or "refresh"
    jti: str  # unique token ID for revocation


def create_access_token(user_id: int, role: str) -> str:
    """Create a short-lived access token.

    Args:
        user_id: The database ID of the authenticated user.
        role: The user's role.

    Returns:
        Encoded JWT access token string.
    """
    settings = get_settings()
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=settings.auth.access_token_expire_minutes
    )
    payload: dict[str, Any] = {  # JWT payload values are heterogeneous (str, datetime, int)
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "type": "access",
        "jti": uuid.uuid4().hex,
    }
    token: str = jwt.encode(payload, settings.auth.jwt_secret_key, algorithm=_JWT_ALGORITHM)
    return token


def create_refresh_token(user_id: int) -> str:
    """Create a longer-lived refresh token.

    Args:
        user_id: The database ID of the authenticated user.

    Returns:
        Encoded JWT refresh token string.
    """
    settings = get_settings()
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        days=settings.auth.refresh_token_expire_days
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": "",  # refresh tokens don't carry role — re-fetched on refresh
        "exp": expire,
        "type": "refresh",
        "jti": uuid.uuid4().hex,
    }
    token: str = jwt.encode(payload, settings.auth.jwt_secret_key, algorithm=_JWT_ALGORITHM)
    return token


async def revoke_token(jti: str, ttl_seconds: int = 1800) -> None:
    """Add a token JTI to the revocation denylist in Redis.

    Args:
        jti: The unique token identifier (from JWT 'jti' claim).
        ttl_seconds: Time to keep in denylist (default: 30 min = access token lifetime).
    """
    try:
        from app.core.redis import get_redis

        redis_client = await get_redis()
        await redis_client.setex(f"auth:revoked:{jti}", ttl_seconds, "1")
    except Exception as e:
        logger.warning(
            "auth.token.revocation_failed",
            jti=jti,
            error=str(e),
            error_type=type(e).__name__,
        )


async def is_token_revoked(jti: str) -> bool:
    """Check if a token JTI has been revoked.

    Args:
        jti: The unique token identifier.

    Returns:
        True if the token is in the revocation denylist.
    """
    if not jti:
        return False
    try:
        from app.core.redis import get_redis

        redis_client = await get_redis()
        result = await redis_client.get(f"auth:revoked:{jti}")
        return result is not None
    except Exception:
        logger.warning(
            "auth.token.revocation_check_degraded",
            jti=jti,
            detail="Redis unavailable - token revocation check skipped (fail-open)",
        )
        return False  # Redis down = allow (fail-open for availability, logged for operators)


def decode_token(token: str) -> TokenPayload | None:
    """Decode and validate a JWT token.

    Args:
        token: The encoded JWT token string.

    Returns:
        TokenPayload if valid, None if invalid/expired.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[_JWT_ALGORITHM],
        )
        return TokenPayload(
            sub=int(payload["sub"]),
            role=str(payload.get("role", "")),
            exp=datetime.datetime.fromtimestamp(float(payload["exp"]), tz=datetime.UTC),
            type=str(payload.get("type", "access")),
            jti=str(payload.get("jti", "")),
        )
    except (InvalidTokenError, KeyError, ValueError) as e:
        logger.warning("auth.token.decode_failed", error=str(e))
        return None
