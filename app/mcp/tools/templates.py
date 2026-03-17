"""Template and component tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.logging import get_logger
from app.mcp import MCPContext
from app.mcp.formatting import format_simple_result, to_dict

logger = get_logger(__name__)


def register_template_tools(mcp: FastMCP) -> None:
    """Register template and component tools."""

    @mcp.tool()
    async def list_templates(
        ctx: MCPContext,
        category: str | None = None,
        limit: int = 20,
    ) -> str:
        """List available email templates in the Hub. Templates are pre-built \
HTML email layouts (promotional, transactional, newsletter, notification) with \
slot-based sections for content injection.

Filter by category to narrow results. Returns template metadata (name, category, \
section count, last modified) without full HTML.

Output: Template list with metadata."""
        # Template listing requires project context and auth — not yet available in MCP
        # Will be enabled when MCP auth is fully wired to FastAPI dependency injection
        return format_simple_result(
            {
                "info": "Template listing requires project context. Use the REST API at /api/v1/templates for full access."
            },
            "Templates",
        )

    @mcp.tool()
    async def search_components(
        query: str,
        ctx: MCPContext,
        category: str | None = None,
        compatible_with: list[str] | None = None,
        limit: int = 10,
    ) -> str:
        """Search the reusable email component library. Components are self-contained \
HTML blocks (headers, footers, CTAs, hero sections, product cards) that can be \
assembled into templates.

Filter by category (header, footer, cta, hero, product, social, divider) and/or \
client compatibility (only return components tested against specified clients).

Output: Matching components with category, compatibility info, and preview HTML."""
        try:
            from app.core.database import get_db_context
            from app.knowledge.component_search import ComponentSearchService

            async with get_db_context() as db:
                service = ComponentSearchService(db)
                results = await service.search_components(
                    query,
                    category=category,
                    compatible_with=compatible_with,
                    limit=min(limit, 50),
                )
            return format_simple_result([to_dict(r) for r in results], "Components")
        except Exception:
            logger.exception("mcp.tool_error", tool="search_components")
            return "Component search failed due to an internal error."
