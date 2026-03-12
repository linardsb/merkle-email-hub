"""Authentication dependencies for each ESP's auth pattern."""

import uuid

from fastapi import Header, HTTPException

# In-memory token store for SFMC/Adobe OAuth flows (cleared on restart)
_issued_tokens: dict[str, str] = {}


def issue_token(client_id: str) -> str:
    """Issue a new access token for a client, return the token string."""
    token = str(uuid.uuid4())
    _issued_tokens[token] = client_id
    return token


def _validate_bearer(authorization: str) -> str:
    """Extract and return bearer token from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail={"message": "Invalid authorization header format"}
        )
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail={"message": "Empty bearer token"})
    return token


async def require_braze_auth(authorization: str = Header(...)) -> str:
    """Braze auth: any non-empty Bearer token is accepted."""
    return _validate_bearer(authorization)


async def require_sfmc_auth(authorization: str = Header(...)) -> str:
    """SFMC auth: Bearer token must have been issued via /sfmc/v2/token."""
    token = _validate_bearer(authorization)
    if token not in _issued_tokens:
        raise HTTPException(status_code=401, detail={"message": "Invalid or expired access token"})
    return token


async def require_adobe_auth(authorization: str = Header(...)) -> str:
    """Adobe auth: Bearer token must have been issued via /adobe/ims/token/v3."""
    token = _validate_bearer(authorization)
    if token not in _issued_tokens:
        raise HTTPException(status_code=401, detail={"message": "Invalid or expired access token"})
    return token


async def require_taxi_auth(x_api_key: str = Header(...)) -> str:
    """Taxi auth: any non-empty X-API-Key header."""
    if not x_api_key.strip():
        raise HTTPException(status_code=401, detail={"message": "Empty API key"})
    return x_api_key
