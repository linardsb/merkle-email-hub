"""MCP resource evaluation tests."""
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false
# mypy: disable-error-code="attr-defined,unused-ignore"

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from app.mcp.resources import register_resources


class TestMCPResources:
    """Test MCP resource definitions."""

    def test_css_property_resource_registered_as_template(self) -> None:
        """CSS property resource is registered as a URI template."""
        mcp = FastMCP("test")
        register_resources(mcp)
        templates: Any = mcp._resource_manager._templates
        assert "ontology://css/{property_name}" in templates

    @pytest.mark.anyio
    async def test_css_property_resource_unknown_property(self) -> None:
        """Unknown CSS property returns not-found message."""
        with patch("app.knowledge.ontology.structured_query.OntologyQueryEngine") as MockEngine:
            MockEngine.return_value.query_property_support = MagicMock(return_value=None)

            mcp = FastMCP("test")
            register_resources(mcp)

            templates: Any = mcp._resource_manager._templates
            template = templates["ontology://css/{property_name}"]
            result = await template.fn(property_name="nonexistent-property")
            assert "not found" in result.lower()

    def test_capabilities_resource_returns_all_flags(self) -> None:
        """Capabilities resource returns all 15 capability flags."""
        with patch("app.core.config.get_settings") as mock_settings:
            s = mock_settings.return_value
            s.qa_chaos.enabled = True
            s.qa_property_testing.enabled = True
            s.qa_outlook_analyzer.enabled = True
            s.qa_deliverability.enabled = True
            s.qa_gmail_predictor.enabled = True
            s.qa_bimi.enabled = True
            s.email_engine.css_compiler_enabled = True
            s.email_engine.schema_injection_enabled = True
            s.rendering.screenshots_enabled = False
            s.rendering.visual_diff_enabled = False
            s.ontology_sync.enabled = True
            s.ai.visual_qa_enabled = True
            s.ai.cost_governor_enabled = True

            mcp = FastMCP("test")
            register_resources(mcp)

            resources: Any = mcp._resource_manager._resources
            resource = resources["hub://capabilities"]
            result = resource.fn()
            caps = json.loads(result)
            expected_keys = {
                "qa_checks",
                "chaos_testing",
                "property_testing",
                "outlook_analyzer",
                "deliverability_scoring",
                "gmail_prediction",
                "bimi_check",
                "css_compiler",
                "schema_injection",
                "screenshots",
                "visual_diff",
                "knowledge_search",
                "ontology_sync",
                "visual_qa",
                "cost_governor",
            }
            assert set(caps.keys()) == expected_keys

    def test_capabilities_resource_matches_config(self) -> None:
        """Capability flags reflect actual config state."""
        with patch("app.core.config.get_settings") as mock_settings:
            s = mock_settings.return_value
            s.qa_chaos.enabled = False
            s.qa_property_testing.enabled = False
            s.qa_outlook_analyzer.enabled = True
            s.qa_deliverability.enabled = True
            s.qa_gmail_predictor.enabled = False
            s.qa_bimi.enabled = True
            s.email_engine.css_compiler_enabled = True
            s.email_engine.schema_injection_enabled = False
            s.rendering.screenshots_enabled = True
            s.rendering.visual_diff_enabled = False
            s.ontology_sync.enabled = False
            s.ai.visual_qa_enabled = False
            s.ai.cost_governor_enabled = True

            mcp = FastMCP("test")
            register_resources(mcp)

            resources: Any = mcp._resource_manager._resources
            caps = json.loads(resources["hub://capabilities"].fn())
            assert caps["qa_checks"] is True  # always True
            assert caps["chaos_testing"] is False
            assert caps["outlook_analyzer"] is True
            assert caps["screenshots"] is True
            assert caps["cost_governor"] is True
