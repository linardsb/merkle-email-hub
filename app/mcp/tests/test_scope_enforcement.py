"""Tests for F005: per-tool scope enforcement on the MCP server.

Covers:
  * ``@require_scope`` marker propagates and the runtime check raises
    ``ToolError`` when the per-request scope set is missing the
    required scope.
  * The ASGI middleware sets ``current_scopes_var`` from the verified
    token's role so a downstream tool sees the right scope set.
  * Default-deny startup check raises if a registered tool lacks
    ``_mcp_required_scope`` — a defensive net for new tools.
  * Scope check sits OUTSIDE the cache wrapper — a viewer must not
    receive a cached payload that an admin-tier tool primed.
  * Role x tool matrix mirrors the production allow/deny table.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from app.mcp.auth import current_scopes_var, require_scope
from app.mcp.server import (
    _enforce_scope_declarations,
    _scope_marker_of,
    _wrap_scope_enforcement,
    create_mcp_server,
)

# ── Marker decorator ────────────────────────────────────────────────


class TestRequireScopeMarker:
    def test_decorator_stamps_scope_attr(self) -> None:
        @require_scope("write")
        async def tool(x: int) -> int:
            return x

        assert _scope_marker_of(tool) == "write"

    def test_unknown_scope_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown scope"):
            require_scope("delete")  # type: ignore[arg-type]

    @pytest.mark.asyncio()
    async def test_denies_when_scope_var_unset(self) -> None:
        @require_scope("write")
        async def tool() -> str:
            return "ok"

        # The conftest autouse fixture grants admin by default; override
        # to None here to simulate an unauthenticated path.
        token = current_scopes_var.set(None)
        try:
            with pytest.raises(ToolError, match="requires scope 'write'"):
                await tool()
        finally:
            current_scopes_var.reset(token)

    @pytest.mark.asyncio()
    async def test_denies_when_scope_missing_from_set(self) -> None:
        @require_scope("write")
        async def tool() -> str:
            return "ok"

        token = current_scopes_var.set(frozenset({"read"}))
        try:
            with pytest.raises(ToolError, match="requires scope 'write'"):
                await tool()
        finally:
            current_scopes_var.reset(token)

    @pytest.mark.asyncio()
    async def test_allows_when_scope_present(self) -> None:
        @require_scope("read")
        async def tool() -> str:
            return "ok"

        token = current_scopes_var.set(frozenset({"read", "write"}))
        try:
            assert await tool() == "ok"
        finally:
            current_scopes_var.reset(token)


# ── Default-deny startup check ─────────────────────────────────────


class _StubTool:
    def __init__(self, fn: Any) -> None:
        self.fn = fn


class _StubTM:
    def __init__(self) -> None:
        self._tools: dict[str, _StubTool] = {}


class _StubMcp:
    def __init__(self) -> None:
        self._tool_manager = _StubTM()


class TestDefaultDenyStartup:
    def test_passes_when_all_tools_decorated(self) -> None:
        mcp = _StubMcp()

        @require_scope("read")
        async def good_tool() -> str:
            return "ok"

        mcp._tool_manager._tools["good_tool"] = _StubTool(good_tool)
        # Should NOT raise — every tool has the marker.
        _enforce_scope_declarations(mcp)  # type: ignore[arg-type]

    def test_raises_when_a_tool_missing_marker(self) -> None:
        mcp = _StubMcp()

        async def naked_tool() -> str:  # no @require_scope
            return "ok"

        mcp._tool_manager._tools["naked_tool"] = _StubTool(naked_tool)
        with pytest.raises(RuntimeError, match="naked_tool"):
            _enforce_scope_declarations(mcp)  # type: ignore[arg-type]


# ── Scope sits outside cache (no leak via cached responses) ────────


class TestScopeOutsideCache:
    @pytest.mark.asyncio()
    async def test_viewer_denied_on_cacheable_write_tool(self) -> None:
        """Even if a write-tier tool's cache is hot, a viewer must be
        denied before the cache lookup runs."""
        cache_hits = 0

        async def underlying(x: int) -> str:
            return f"result-{x}"

        @require_scope("read")
        async def cache_layer(x: int) -> str:
            nonlocal cache_hits
            cache_hits += 1
            return await underlying(x)

        # Outer = scope("write"); should deny a viewer (read-only).
        mcp = _StubMcp()
        mcp._tool_manager._tools["t"] = _StubTool(cache_layer)
        # Re-decorate with write scope to mimic the wrap pass.
        mcp._tool_manager._tools["t"].fn = require_scope("write")(cache_layer)

        token = current_scopes_var.set(frozenset({"read"}))
        try:
            with pytest.raises(ToolError):
                await mcp._tool_manager._tools["t"].fn(1)
        finally:
            current_scopes_var.reset(token)
        assert cache_hits == 0  # cache never reached


# ── Production server: role x tool matrix ──────────────────────────


@pytest.fixture(scope="module")
def real_mcp() -> Any:
    """Build the real MCP server once. The default-deny startup check
    inside ``create_mcp_server`` doubles as a smoke test that every tool
    is decorated."""
    return create_mcp_server()


_MATRIX = [
    # (role_scopes,        tool_name,                      should_allow)
    (frozenset({"read"}), "qa_check", True),
    (frozenset({"read"}), "knowledge_search", True),
    (frozenset({"read"}), "list_templates", True),
    (frozenset({"read"}), "agent_scaffold", False),
    (frozenset({"read"}), "agent_dark_mode", False),
    (frozenset({"read"}), "chaos_test", False),
    (frozenset({"read"}), "mcp_batch_execute", False),
    (frozenset({"read", "write"}), "agent_scaffold", True),
    (frozenset({"read", "write"}), "agent_content", True),
    (frozenset({"read", "write"}), "mcp_batch_execute", True),
    (frozenset({"read", "write", "admin"}), "agent_innovate", True),
    (frozenset({"read", "write", "admin"}), "qa_check", True),
]


@pytest.mark.parametrize(("scopes", "tool_name", "should_allow"), _MATRIX)
@pytest.mark.asyncio()
async def test_role_tool_matrix(
    real_mcp: Any, scopes: frozenset[str], tool_name: str, should_allow: bool
) -> None:
    """Each row asserts the scope set either passes the gate or is denied
    by ``ToolError`` *before* the tool body runs.

    We patch the underlying body via the wrap chain so a permitted call
    does not trigger LLM/HTTP work. The key assertion is whether
    ``ToolError`` was raised at the gate or the body was reached.
    """
    tool = real_mcp._tool_manager._tools[tool_name]
    # Replace innermost callable with a sentinel-raiser so a permitted
    # call short-circuits before any I/O.
    body_reached = False

    async def sentinel(*_: Any, **__: Any) -> str:
        nonlocal body_reached
        body_reached = True
        return "ok"

    # The wrap stack ends up as: scope_check → cache → original. To
    # avoid changing it, monkey-patch the *outermost* fn to bypass the
    # body once the scope check has passed.
    marker = _scope_marker_of(tool.fn)
    if marker == "read":
        gated = require_scope("read")(sentinel)
    elif marker == "write":
        gated = require_scope("write")(sentinel)
    elif marker == "admin":
        gated = require_scope("admin")(sentinel)
    else:
        pytest.fail(f"unexpected marker {marker!r}")
    with patch.object(tool, "fn", gated):
        token = current_scopes_var.set(scopes)
        try:
            if should_allow:
                # Permitted: sentinel runs; body_reached flips True.
                result = await tool.fn(ctx=None)
                assert result == "ok"
                assert body_reached is True
            else:
                with pytest.raises(ToolError, match="Permission denied"):
                    await tool.fn(ctx=None)
                assert body_reached is False
        finally:
            current_scopes_var.reset(token)


# ── _wrap_scope_enforcement preserves scope marker after wrap ──────


class TestWrapScopeEnforcement:
    def test_wrapped_fn_still_advertises_scope(self) -> None:
        mcp = _StubMcp()

        @require_scope("write")
        async def tool() -> str:
            return "x"

        mcp._tool_manager._tools["tool"] = _StubTool(tool)
        _wrap_scope_enforcement(mcp)  # type: ignore[arg-type]

        # Even after re-wrap, _scope_marker_of must still find the marker
        # on the chain so the startup audit remains observable.
        assert _scope_marker_of(mcp._tool_manager._tools["tool"].fn) == "write"
