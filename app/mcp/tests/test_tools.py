"""Tests for MCP tool handlers."""
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import pytest

from app.mcp.server import create_mcp_server


@pytest.fixture
def mcp() -> object:
    return create_mcp_server()


class TestMCPServerCreation:
    def test_server_creates_with_tools(self, mcp: object) -> None:
        """Server should have registered tools."""
        tools = mcp._tool_manager._tools  # type: ignore[attr-defined]
        assert len(tools) > 0

    def test_server_has_expected_tools(self, mcp: object) -> None:
        tools = set(mcp._tool_manager._tools)  # type: ignore[attr-defined]
        expected = {
            "qa_check",
            "email_production_readiness",
            "chaos_test",
            "outlook_analyze",
            "gmail_predict",
            "knowledge_search",
            "css_support_check",
            "safe_css_alternatives",
            "css_optimize",
            "inject_schema_markup",
            "email_visual_check",
            "visual_diff",
            "list_templates",
            "search_components",
            "ai_cost_status",
            "deliverability_score",
            "bimi_check",
        }
        assert expected.issubset(tools), f"Missing tools: {expected - tools}"

    def test_server_has_instructions(self, mcp: object) -> None:
        assert "Email Innovation Hub" in (mcp._mcp_server.instructions or "")  # type: ignore[attr-defined]

    def test_server_stateless_mode(self, mcp: object) -> None:
        assert mcp.settings.stateless_http is True  # type: ignore[attr-defined]

    def test_tool_descriptions_are_substantive(self, mcp: object) -> None:
        """Every tool description should be 30+ words (email-domain-aware)."""
        for name, tool in mcp._tool_manager._tools.items():  # type: ignore[attr-defined]
            desc = tool.description or ""
            word_count = len(desc.split())
            assert word_count >= 30, (
                f"Tool '{name}' description too short ({word_count} words). "
                "MCP tool descriptions should teach LLMs about email constraints."
            )


class TestMCPResources:
    def test_server_has_resources(self, mcp: object) -> None:
        """Server should have registered resources."""
        assert mcp._resource_manager is not None  # type: ignore[attr-defined]
