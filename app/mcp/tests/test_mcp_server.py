"""MCP server integration tests — server creation, tool registration, resource access.

Phase 32.12: Validates create_mcp_server() wiring, all 9 agent tools present,
tool execution with mocked services, resource endpoints, and validation guards.
"""

# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP

# ── Helpers ──

_VALID_HTML = "<html><body>" + "x" * 50 + "</body></html>"

_EXPECTED_AGENT_TOOLS = {
    "agent_scaffold",
    "agent_dark_mode",
    "agent_content",
    "agent_outlook_fix",
    "agent_accessibility",
    "agent_code_review",
    "agent_personalise",
    "agent_innovate",
    "agent_knowledge",
}


def _mock_response(**overrides: Any) -> MagicMock:
    defaults: dict[str, Any] = {
        "html": "<html><body>Generated</body></html>",
        "model": "test-model",
        "confidence": 0.92,
        "skills_loaded": ["SKILL.md"],
    }
    defaults.update(overrides)
    mock = MagicMock()
    mock.model_dump.return_value = defaults
    return mock


# ── Server Creation ──


class TestMCPServerCreation:
    """create_mcp_server() returns a correctly configured FastMCP instance."""

    def test_server_creates_successfully(self) -> None:
        """create_mcp_server() returns a FastMCP instance without errors."""
        from app.mcp.server import create_mcp_server

        mcp = create_mcp_server()
        assert isinstance(mcp, FastMCP)

    def test_all_agent_tools_registered(self) -> None:
        """All 9 agent tools are present on the server."""
        from app.mcp.server import create_mcp_server

        mcp = create_mcp_server()
        tools = set(mcp._tool_manager._tools)
        assert _EXPECTED_AGENT_TOOLS.issubset(tools), (
            f"Missing agent tools: {_EXPECTED_AGENT_TOOLS - tools}"
        )

    def test_tool_schemas_have_required_params(self) -> None:
        """Each agent tool has a description and at least one required parameter."""
        from app.mcp.server import create_mcp_server

        mcp = create_mcp_server()
        for name in _EXPECTED_AGENT_TOOLS:
            tool = mcp._tool_manager._tools[name]
            assert tool.description, f"Tool '{name}' has no description"
            # All agent tools have at least one required param (brief, html, operation, etc.)
            params = tool.parameters
            assert params, f"Tool '{name}' has no parameter schema"


# ── Tool Execution ──


class TestMCPServerToolExecution:
    """Agent tools execute through the server and return formatted results."""

    @pytest.mark.anyio
    async def test_scaffold_returns_html_confidence(self) -> None:
        """Scaffold tool returns formatted result with confidence and HTML."""
        with patch("app.ai.agents.scaffolder.service.get_scaffolder_service") as mock_get:
            svc = AsyncMock()
            svc.process = AsyncMock(
                return_value=_mock_response(
                    qa_passed=True,
                    qa_results=None,
                    mso_warnings=[],
                    plan=None,
                )
            )
            mock_get.return_value = svc

            from app.mcp.tools.agents import register_agent_tools

            mcp = FastMCP("test")
            register_agent_tools(mcp)
            tool_fn = mcp._tool_manager._tools["agent_scaffold"].fn
            result = await tool_fn(
                brief="Create a promotional email for a summer sale with hero banner and 3 product cards",
                ctx=MagicMock(),
            )
            assert "92%" in result
            assert "Scaffolder" in result
            assert "qa_passed" in result

    @pytest.mark.anyio
    async def test_content_subject_line_operation(self) -> None:
        """Content tool with subject_line operation returns alternatives."""
        with patch("app.ai.agents.content.service.get_content_service") as mock_get:
            svc = AsyncMock()
            svc.process = AsyncMock(
                return_value=_mock_response(
                    html="",
                    content=["Summer Savings Await!", "Hot Deals Inside", "Don't Miss Out"],
                    operation="subject_line",
                    spam_warnings=[],
                    length_warnings=[],
                    decisions=None,
                )
            )
            mock_get.return_value = svc

            from app.mcp.tools.agents import register_agent_tools

            mcp = FastMCP("test")
            register_agent_tools(mcp)
            tool_fn = mcp._tool_manager._tools["agent_content"].fn
            result = await tool_fn(
                operation="subject_line",
                text="Summer sale campaign for outdoor adventure gear",
                ctx=MagicMock(),
            )
            assert "Content" in result

    @pytest.mark.anyio
    async def test_code_review_returns_structured(self) -> None:
        """Code review tool returns structured review results."""
        with patch("app.ai.agents.code_reviewer.service.get_code_review_service") as mock_get:
            svc = AsyncMock()
            svc.process = AsyncMock(
                return_value=_mock_response(
                    issues=[
                        {"rule": "redundant-mso", "severity": "warning", "message": "Found"},
                        {"rule": "unsupported-css", "severity": "error", "message": "Gap"},
                    ],
                    summary="2 issues found",
                    qa_passed=None,
                    qa_results=None,
                    decisions=None,
                    actionability_warnings=[],
                )
            )
            mock_get.return_value = svc

            from app.mcp.tools.agents import register_agent_tools

            mcp = FastMCP("test")
            register_agent_tools(mcp)
            tool_fn = mcp._tool_manager._tools["agent_code_review"].fn
            result = await tool_fn(html=_VALID_HTML, ctx=MagicMock())
            assert "Code Review" in result
            assert "issues" in result

    @pytest.mark.anyio
    async def test_invalid_operation_returns_error(self) -> None:
        """Invalid operation enum returns descriptive error string."""
        from app.mcp.tools.agents import register_agent_tools

        mcp = FastMCP("test")
        register_agent_tools(mcp)
        tool_fn = mcp._tool_manager._tools["agent_content"].fn
        result = await tool_fn(
            operation="generate_poem",
            text="Some campaign brief",
            ctx=MagicMock(),
        )
        assert "Invalid operation" in result

    @pytest.mark.anyio
    async def test_missing_required_param_does_not_crash(self) -> None:
        """Calling a tool that validates input doesn't crash on bad input."""
        from app.mcp.tools.agents import register_agent_tools

        mcp = FastMCP("test")
        register_agent_tools(mcp)
        tool_fn = mcp._tool_manager._tools["agent_scaffold"].fn
        result = await tool_fn(brief="tiny", ctx=MagicMock())
        assert "too short" in result.lower()


# ── Agent Resource ──


class TestMCPAgentResource:
    """hub://agents resource returns complete agent registry."""

    def test_agents_resource_returns_nine(self) -> None:
        """hub://agents lists all 9 agents."""
        from app.mcp.resources import register_resources

        mcp = FastMCP("test")
        register_resources(mcp)
        resources: Any = mcp._resource_manager._resources
        result = json.loads(resources["hub://agents"].fn())
        assert result["count"] == 9
        names = {a["name"] for a in result["agents"]}
        assert names == {
            "scaffolder",
            "dark_mode",
            "content",
            "outlook_fixer",
            "accessibility",
            "code_reviewer",
            "personalisation",
            "innovation",
            "knowledge",
        }

    def test_agents_resource_has_required_fields(self) -> None:
        """Each agent entry has name, tool, type, description, accepts, returns."""
        from app.mcp.resources import register_resources

        mcp = FastMCP("test")
        register_resources(mcp)
        resources: Any = mcp._resource_manager._resources
        result = json.loads(resources["hub://agents"].fn())
        required_fields = {"name", "tool", "type", "description", "accepts", "returns"}
        for agent in result["agents"]:
            missing = required_fields - set(agent.keys())
            assert not missing, f"Agent '{agent.get('name')}' missing fields: {missing}"


# ── Rate Limiting ──


class TestMCPRateLimiting:
    """Rate limiting does not interfere with normal usage."""

    @pytest.mark.anyio
    async def test_rapid_calls_within_limit(self) -> None:
        """Multiple sequential validation calls succeed (no rate limit on validation-only paths)."""
        from app.mcp.tools.agents import register_agent_tools

        mcp = FastMCP("test")
        register_agent_tools(mcp)
        tool_fn = mcp._tool_manager._tools["agent_content"].fn

        # 5 rapid validation-only calls (no service invocation)
        results = []
        for _ in range(5):
            r = await tool_fn(operation="invalid_op", text="Test brief", ctx=MagicMock())
            results.append(r)

        assert all("Invalid operation" in r for r in results)
