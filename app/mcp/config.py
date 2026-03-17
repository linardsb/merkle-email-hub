"""MCP server configuration helpers."""

from __future__ import annotations

import fnmatch

from app.core.config import get_settings


def is_tool_allowed(tool_name: str) -> bool:
    """Check if a tool name passes the operator allowlist filter."""
    settings = get_settings()
    allowlist = settings.mcp.tool_allowlist
    if not allowlist:
        return True  # empty = all allowed
    return any(fnmatch.fnmatch(tool_name, pattern) for pattern in allowlist)
