"""Hub MCP server factory and transport configuration."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.logging import get_logger
from app.mcp.config import is_tool_allowed
from app.mcp.resources import register_resources
from app.mcp.tools.ai import register_ai_tools
from app.mcp.tools.email import register_email_tools
from app.mcp.tools.knowledge import register_knowledge_tools
from app.mcp.tools.qa import register_qa_tools
from app.mcp.tools.rendering import register_rendering_tools
from app.mcp.tools.templates import register_template_tools

logger = get_logger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure the Hub MCP server with all tools and resources.

    Returns a FastMCP instance ready to be mounted or run standalone.
    """
    mcp = FastMCP(
        name="Merkle Email Hub",
        instructions=(
            "You are connected to the Merkle Email Innovation Hub — a comprehensive platform "
            "for building, testing, and optimizing HTML emails. Use the available tools to "
            "validate email HTML against client compatibility, check deliverability, optimize "
            "CSS for email clients, search email development knowledge, and more. "
            "Start with `qa_check` for basic validation, or `email_production_readiness` "
            "for comprehensive pre-send analysis."
        ),
        stateless_http=True,
        json_response=True,
    )

    # Register tool groups
    register_qa_tools(mcp)
    register_knowledge_tools(mcp)
    register_email_tools(mcp)
    register_rendering_tools(mcp)
    register_template_tools(mcp)
    register_ai_tools(mcp)

    # Apply tool allowlist filter — remove tools not in the operator allowlist
    _apply_tool_allowlist(mcp)

    # Register resources
    register_resources(mcp)

    tool_count = len(mcp._tool_manager._tools)
    logger.info("mcp.server_created", tool_count=tool_count)

    return mcp


def _apply_tool_allowlist(mcp: FastMCP) -> None:
    """Remove tools that don't match the operator allowlist."""
    tools = mcp._tool_manager._tools
    blocked = [name for name in tools if not is_tool_allowed(name)]
    for name in blocked:
        del tools[name]
        logger.info("mcp.tool_blocked_by_allowlist", tool=name)


# Module-level singleton for mounting
_mcp_server: FastMCP | None = None


def get_mcp_server() -> FastMCP:
    """Get or create the singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = create_mcp_server()
    return _mcp_server
