"""Rendering and visual QA tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.logging import get_logger
from app.mcp import MCPContext
from app.mcp.formatting import format_simple_result, to_dict

logger = get_logger(__name__)

_MAX_HTML_SIZE = 500_000


def register_rendering_tools(mcp: FastMCP) -> None:
    """Register rendering tools."""

    @mcp.tool()
    async def email_visual_check(
        html: str,
        ctx: MCPContext,
        clients: list[str] | None = None,
    ) -> str:
        """Capture screenshots of how an HTML email renders across email clients using \
Playwright browser automation. Available client profiles: gmail (style stripping), \
outlook_2019 (Word engine CSS injection), apple_mail (WebKit), outlook_dark (dark mode), \
mobile_ios (375px viewport).

Each screenshot simulates the client's rendering constraints (Gmail removes <style> tags, \
Outlook injects Word CSS, etc.) to show realistic previews.

Requires RENDERING__SCREENSHOTS_ENABLED=true. Returns base64 PNG screenshots per client.

Output: Per-client screenshot data with rendering notes."""
        if len(html) > _MAX_HTML_SIZE:
            return f"HTML too large ({len(html):,} chars). Maximum is {_MAX_HTML_SIZE:,} chars."
        try:
            from app.core.config import get_settings

            if not get_settings().rendering.screenshots_enabled:
                return "Screenshot rendering is not enabled. Set RENDERING__SCREENSHOTS_ENABLED=true to activate."

            from app.core.database import get_db_context
            from app.rendering.schemas import ScreenshotRequest
            from app.rendering.service import RenderingService

            request = ScreenshotRequest(
                html=html,
                clients=clients or ["gmail_web", "outlook_2019", "apple_mail"],
            )
            async with get_db_context() as db:
                service = RenderingService(db)
                result = await service.render_screenshots(request)
            # Don't send full base64 images — just metadata
            summary: list[dict[str, object]] = []
            for screenshot in to_dict(result).get("screenshots", []):
                summary.append(
                    {
                        "client": screenshot.get("client_name"),
                        "width": screenshot.get("width"),
                        "height": screenshot.get("height"),
                        "size_bytes": len(screenshot.get("image_base64", "")),
                    }
                )
            return format_simple_result({"screenshots": summary}, "Visual Check")
        except Exception:
            logger.exception("mcp.tool_error", tool="email_visual_check")
            return "Visual check failed due to an internal error."

    @mcp.tool()
    async def visual_diff(
        current_html: str,
        baseline_html: str,
        ctx: MCPContext,
        client: str = "gmail",
    ) -> str:
        """Compare two versions of an HTML email visually using ODiff pixel comparison. \
Renders both versions through the specified client profile, then computes a diff image \
highlighting changed regions.

Use this to verify that code changes don't cause unintended visual regressions. \
A diff percentage above 1% typically indicates a visible change.

Output: Diff percentage, changed region count, and whether the change exceeds threshold."""
        try:
            from app.core.config import get_settings

            if not get_settings().rendering.visual_diff_enabled:
                return "Visual diff is not enabled. Set RENDERING__VISUAL_DIFF_ENABLED=true to activate."

            return format_simple_result(
                {
                    "status": "Visual diff implementation pending — use `email_visual_check` to capture screenshots for manual comparison."
                },
                "Visual Diff",
            )
        except Exception:
            logger.exception("mcp.tool_error", tool="visual_diff")
            return "Visual diff failed due to an internal error."
