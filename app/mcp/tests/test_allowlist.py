"""MCP tool allowlist filtering tests."""
# mypy: disable-error-code="attr-defined,unused-ignore"

from __future__ import annotations

from unittest.mock import patch

from app.mcp.config import is_tool_allowed
from app.mcp.server import create_mcp_server


class TestAllowlistFiltering:
    """Test tool allowlist fnmatch-based filtering."""

    def test_empty_allowlist_allows_all(self) -> None:
        """Empty allowlist allows all registered tools."""
        with patch("app.mcp.config.get_settings") as mock_settings:
            mock_settings.return_value.mcp.tool_allowlist = []
            server = create_mcp_server()
            tools = server._tool_manager._tools  # type: ignore[attr-defined]
            assert len(tools) >= 17

    def test_specific_allowlist_filters(self) -> None:
        """Pattern `qa_*` keeps only QA-prefixed tools."""
        with patch("app.mcp.config.get_settings") as mock_settings:
            mock_settings.return_value.mcp.tool_allowlist = ["qa_*"]
            server = create_mcp_server()
            tools = set(server._tool_manager._tools)  # type: ignore[attr-defined]
            for name in tools:
                assert name.startswith("qa_"), f"Unexpected tool: {name}"
            assert len(tools) >= 1

    def test_multiple_patterns(self) -> None:
        """Multiple patterns keep matching tool groups."""
        with patch("app.mcp.config.get_settings") as mock_settings:
            mock_settings.return_value.mcp.tool_allowlist = ["qa_*", "knowledge_*"]
            server = create_mcp_server()
            tools = set(server._tool_manager._tools)  # type: ignore[attr-defined]
            for name in tools:
                assert name.startswith(("qa_", "knowledge_")), f"Unexpected tool: {name}"

    def test_no_matching_pattern_removes_all(self) -> None:
        """Non-matching pattern removes all tools."""
        with patch("app.mcp.config.get_settings") as mock_settings:
            mock_settings.return_value.mcp.tool_allowlist = ["nonexistent_*"]
            server = create_mcp_server()
            tools = server._tool_manager._tools  # type: ignore[attr-defined]
            assert len(tools) == 0

    def test_is_tool_allowed_fnmatch(self) -> None:
        """Direct unit test of is_tool_allowed with various patterns."""
        with patch("app.mcp.config.get_settings") as mock_settings:
            # Wildcard pattern
            mock_settings.return_value.mcp.tool_allowlist = ["qa_*"]
            assert is_tool_allowed("qa_check") is True
            assert is_tool_allowed("knowledge_search") is False

            # Exact match
            mock_settings.return_value.mcp.tool_allowlist = ["bimi_check"]
            assert is_tool_allowed("bimi_check") is True
            assert is_tool_allowed("qa_check") is False

            # Suffix pattern
            mock_settings.return_value.mcp.tool_allowlist = ["*_check"]
            assert is_tool_allowed("qa_check") is True
            assert is_tool_allowed("bimi_check") is True
            assert is_tool_allowed("css_optimize") is False
