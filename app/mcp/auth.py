"""MCP authentication via existing Hub bearer tokens.

MCP clients pass the same bearer token used for REST API calls.
This module provides token verification using the Hub's JWT infrastructure
plus the per-tool scope-enforcement decorator that gates write/admin tools
against the caller's role-derived scopes.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, Literal, TypeVar

from mcp.server.fastmcp.exceptions import ToolError

from app.core.logging import get_logger

logger = get_logger(__name__)

Scope = Literal["read", "write", "admin"]
_ALLOWED_SCOPES: frozenset[str] = frozenset({"read", "write", "admin"})

# Per-request scope set, populated by ``MCPAuthMiddleware`` before the
# request reaches the FastMCP tool dispatcher. The middleware and the
# tool handler run in the same asyncio task chain, so ContextVar is the
# cleanest cross-cutting transport that does not require touching the
# FastMCP context object's internals.
current_scopes_var: ContextVar[frozenset[str] | None] = ContextVar(
    "mcp_current_scopes", default=None
)

F = TypeVar("F", bound=Callable[..., Any])


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


def require_scope(scope: Scope) -> Callable[[F], F]:
    """Marker decorator: declare the scope a tool requires to execute.

    Wraps the tool with a permission check that reads the per-request
    scope set from ``current_scopes_var`` and raises ``ToolError`` if
    the required scope is missing. Also tags the wrapper with
    ``_mcp_required_scope`` so the server-side default-deny startup
    check can audit tool registrations.

    Decorator order at definition site MUST be::

        @mcp.tool()
        @require_scope("write")
        async def my_tool(...): ...

    so FastMCP sees the wrapped function. The cache wrapper applied in
    ``_wrap_cacheable_tools`` runs *inside* this scope check (deny
    before cache lookup).
    """
    if scope not in _ALLOWED_SCOPES:
        raise ValueError(f"unknown scope {scope!r}; expected one of {sorted(_ALLOWED_SCOPES)}")

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            scopes = current_scopes_var.get()
            if scopes is None or scope not in scopes:
                tool_name = getattr(fn, "__name__", "<tool>")
                logger.warning(
                    "mcp.scope_denied",
                    tool=tool_name,
                    required_scope=scope,
                    granted_scopes=sorted(scopes) if scopes else [],
                )
                raise ToolError(f"Permission denied: tool '{tool_name}' requires scope '{scope}'")
            return await fn(*args, **kwargs)

        wrapper._mcp_required_scope = scope  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
