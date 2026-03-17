"""MCP authentication via existing Hub bearer tokens.

MCP clients pass the same bearer token used for REST API calls.
This module provides token verification using the Hub's JWT infrastructure.
"""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_mcp_token(token: str) -> dict[str, str] | None:
    """Verify a bearer token and return access info.

    Returns a dict with client_id and scopes if valid, None otherwise.
    """
    from app.auth.token import decode_token

    try:
        payload = decode_token(token)
        if payload is None:
            return None
        return {
            "client_id": str(payload.sub),
            "role": payload.role,
            "scopes": ",".join(_role_to_scopes(payload.role)),
        }
    except Exception:
        logger.debug("mcp.auth_failed", reason="token_decode_error")
        return None


def _role_to_scopes(role: str) -> list[str]:
    """Map Hub roles to MCP scopes."""
    scope_map = {
        "admin": ["read", "write", "admin"],
        "developer": ["read", "write"],
        "viewer": ["read"],
    }
    return scope_map.get(role, ["read"])
