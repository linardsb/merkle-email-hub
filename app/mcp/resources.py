"""MCP resource definitions — read-only access to Hub data."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

_AGENT_REGISTRY = [
    {
        "name": "scaffolder",
        "tool": "agent_scaffold",
        "type": "generator",
        "description": "Generate email HTML from a campaign brief",
        "accepts": "brief",
        "returns": "html",
    },
    {
        "name": "dark_mode",
        "tool": "agent_dark_mode",
        "type": "transformer",
        "description": "Add dark mode styles to email HTML",
        "accepts": "html",
        "returns": "html",
    },
    {
        "name": "content",
        "tool": "agent_content",
        "type": "generator",
        "description": "Generate email copy (subject lines, CTAs, body text)",
        "accepts": "operation + text",
        "returns": "alternatives",
    },
    {
        "name": "outlook_fixer",
        "tool": "agent_outlook_fix",
        "type": "transformer",
        "description": "Fix Outlook rendering issues in email HTML",
        "accepts": "html",
        "returns": "html",
    },
    {
        "name": "accessibility",
        "tool": "agent_accessibility",
        "type": "transformer",
        "description": "Add WCAG accessibility improvements to email HTML",
        "accepts": "html",
        "returns": "html",
    },
    {
        "name": "code_reviewer",
        "tool": "agent_code_review",
        "type": "analyzer",
        "description": "Review email HTML for quality and compatibility issues",
        "accepts": "html",
        "returns": "issues",
    },
    {
        "name": "personalisation",
        "tool": "agent_personalise",
        "type": "transformer",
        "description": "Inject ESP dynamic content syntax into email HTML",
        "accepts": "html + platform + requirements",
        "returns": "html",
    },
    {
        "name": "innovation",
        "tool": "agent_innovate",
        "type": "generator",
        "description": "Prototype experimental email techniques",
        "accepts": "technique",
        "returns": "prototype + fallback",
    },
    {
        "name": "knowledge",
        "tool": "agent_knowledge",
        "type": "advisor",
        "description": "Answer email development questions with citations",
        "accepts": "question",
        "returns": "answer + sources",
    },
]


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

    @mcp.resource("hub://agents")
    def agent_list() -> str:
        """List all available AI agents with their MCP tool names and capabilities."""
        return json.dumps({"agents": _AGENT_REGISTRY, "count": len(_AGENT_REGISTRY)}, indent=2)

    @mcp.resource("hub://component-tree-schema")
    def component_tree_schema() -> str:
        """JSON Schema for EmailTree — constrained component tree output format."""
        from app.components.tree_schema import export_json_schema

        return json.dumps(export_json_schema(), indent=2)
