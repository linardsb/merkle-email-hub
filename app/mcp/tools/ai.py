"""AI and blueprint tools."""

from __future__ import annotations

import re

from mcp.server.fastmcp import FastMCP

from app.core.logging import get_logger
from app.mcp import MCPContext
from app.mcp.formatting import format_simple_result, to_dict

logger = get_logger(__name__)

_MAX_HTML_SIZE = 500_000
_DOMAIN_PATTERN = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$")


def register_ai_tools(mcp: FastMCP) -> None:
    """Register AI-related tools."""

    @mcp.tool()
    async def ai_cost_status(ctx: MCPContext) -> str:
        """Check the current month's AI cost budget status. Shows total spend, \
remaining budget, and per-model/per-agent breakdowns.

Requires admin or developer role.

Output: Budget status (OK/WARNING/EXCEEDED), spend breakdown, and remaining budget."""
        try:
            from app.ai.cost_governor import CostGovernor
            from app.core.config import get_settings

            settings = get_settings()
            governor = CostGovernor(
                monthly_budget_gbp=settings.ai.monthly_budget_gbp,
                warning_threshold=settings.ai.budget_warning_threshold,
            )
            status = await governor.get_report()
            return format_simple_result(to_dict(status), "AI Cost Status")
        except Exception:
            logger.exception("mcp.tool_error", tool="ai_cost_status")
            return "Cost status check failed due to an internal error."

    @mcp.tool()
    async def deliverability_score(
        html: str,
        ctx: MCPContext,
    ) -> str:
        """Calculate email deliverability prediction score (0-100) across 4 dimensions: \
content quality (spam triggers, text-to-image ratio, link density, scored 0-25), \
HTML hygiene (valid structure, reasonable size, clean CSS, scored 0-25), \
auth readiness (SPF/DKIM/DMARC alignment signals, scored 0-25), \
engagement signals (preview text, subject relevance, CTA clarity, scored 0-25).

This is a heuristic score, not a guarantee of inbox placement, but a strong signal \
for common deliverability issues.

Output: Total score, per-dimension breakdown, and specific issues with fix recommendations."""
        if len(html) > _MAX_HTML_SIZE:
            return f"HTML too large ({len(html):,} chars). Maximum is {_MAX_HTML_SIZE:,} chars."
        try:
            from app.qa_engine.checks.deliverability import get_detailed_result

            score, passed, dimensions, _isp_analysis = get_detailed_result(html)
            return format_simple_result(
                {
                    "score": score,
                    "passed": passed,
                    "dimensions": [to_dict(d) for d in dimensions],
                },
                "Deliverability Score",
            )
        except Exception:
            logger.exception("mcp.tool_error", tool="deliverability_score")
            return "Deliverability scoring failed due to an internal error."

    @mcp.tool()
    async def bimi_check(
        domain: str,
        ctx: MCPContext,
    ) -> str:
        """Check BIMI (Brand Indicators for Message Identification) readiness for a domain. \
Performs DNS lookups for DMARC and BIMI records, validates SVG logo (must be SVG Tiny PS, \
square, no scripts, no external references), and checks CMC (Certified Mark Certificate) status.

BIMI lets your brand logo appear next to emails in Gmail, Apple Mail, and Yahoo, \
significantly boosting open rates and brand recognition.

Output: Readiness checklist (DMARC, BIMI record, SVG, CMC), issues, and suggested TXT record."""
        if not _DOMAIN_PATTERN.match(domain):
            return f"Invalid domain format: `{domain}`. Expected a domain name like `example.com`."
        try:
            from app.qa_engine.bimi.checker import BIMIReadinessChecker

            checker = BIMIReadinessChecker()
            result = await checker.check_domain(domain)
            return format_simple_result(to_dict(result), "BIMI Readiness")
        except Exception:
            logger.exception("mcp.tool_error", tool="bimi_check")
            return "BIMI check failed due to an internal error."
