"""MCP resource definitions — read-only access to Hub data."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:
    """Register MCP resources."""

    @mcp.resource("ontology://css/{property_name}")
    async def css_property_support(property_name: str) -> str:
        """CSS property support data from the caniemail ontology."""
        from app.knowledge.ontology.structured_query import OntologyQueryEngine

        engine = OntologyQueryEngine()
        result = engine.query_property_support(property_name)
        if result is None:
            return f"Property '{property_name}' not found in ontology."
        from dataclasses import asdict

        return json.dumps(asdict(result), indent=2, default=str)

    @mcp.resource("hub://capabilities")
    def hub_capabilities() -> str:
        """List all available Hub capabilities and their enabled/disabled status."""
        from app.core.config import get_settings

        s = get_settings()
        caps = {
            "qa_checks": True,  # always available
            "chaos_testing": s.qa_chaos.enabled,
            "property_testing": s.qa_property_testing.enabled,
            "outlook_analyzer": s.qa_outlook_analyzer.enabled,
            "deliverability_scoring": s.qa_deliverability.enabled,
            "gmail_prediction": s.qa_gmail_predictor.enabled,
            "bimi_check": s.qa_bimi.enabled,
            "css_compiler": s.email_engine.css_compiler_enabled,
            "schema_injection": s.email_engine.schema_injection_enabled,
            "screenshots": s.rendering.screenshots_enabled,
            "visual_diff": s.rendering.visual_diff_enabled,
            "knowledge_search": True,  # always available
            "ontology_sync": s.ontology_sync.enabled,
            "visual_qa": s.ai.visual_qa_enabled,
            "cost_governor": s.ai.cost_governor_enabled,
        }
        return json.dumps(caps, indent=2)
