"""Email engine tools — CSS compilation, schema markup."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.logging import get_logger
from app.mcp import MCPContext
from app.mcp.formatting import format_css_compilation, format_simple_result, to_dict, truncate_html

logger = get_logger(__name__)

_MAX_HTML_SIZE = 500_000


def register_email_tools(mcp: FastMCP) -> None:
    """Register email engine tools."""

    @mcp.tool()
    async def css_optimize(
        html: str,
        ctx: MCPContext,
        target_clients: list[str] | None = None,
    ) -> str:
        """Compile and optimize CSS in HTML email for maximum client compatibility. \
7-stage pipeline: parse, analyze, transform unsupported properties to fallbacks, \
eliminate dead CSS, optimize via Lightning CSS, inline critical styles, sanitize.

Uses the caniemail ontology to know exactly which CSS properties each client supports. \
Automatically converts modern CSS (gap to margin, flexbox to table layout) to \
email-safe equivalents with per-client conditional comments where needed.

Returns compiled HTML with size reduction stats and a list of every CSS conversion applied.

Output: Compiled HTML, original to compiled size comparison, conversion details."""
        if len(html) > _MAX_HTML_SIZE:
            return f"HTML too large ({len(html):,} chars). Maximum is {_MAX_HTML_SIZE:,} chars."
        try:
            from app.email_engine.css_compiler.compiler import EmailCSSCompiler

            compiler = EmailCSSCompiler(target_clients=target_clients)
            result = compiler.compile(html)
            return format_css_compilation(to_dict(result))
        except Exception:
            logger.exception("mcp.tool_error", tool="css_optimize")
            return "CSS optimization failed due to an internal error."

    @mcp.tool()
    async def inject_schema_markup(
        html: str,
        ctx: MCPContext,
        subject: str = "",
    ) -> str:
        """Auto-detect email intent (promotional, transactional, event, newsletter, \
notification) and inject appropriate Schema.org JSON-LD markup. Maps intent to schema \
types: promotional to Product+Offer+DealAnnotation, transactional to Order+TrackAction, \
event to Event+RsvpAction. Extracts entities (prices, dates, tracking numbers, URLs) \
from the HTML to populate schema fields.

Schema markup helps Gmail show rich cards (action buttons, order tracking, event RSVP) \
instead of plain email previews.

Output: Modified HTML with JSON-LD injected, detected intent, and extracted entities."""
        if len(html) > _MAX_HTML_SIZE:
            return f"HTML too large ({len(html):,} chars). Maximum is {_MAX_HTML_SIZE:,} chars."
        try:
            from app.email_engine.schema_markup.classifier import EmailIntentClassifier
            from app.email_engine.schema_markup.injector import SchemaMarkupInjector

            classifier = EmailIntentClassifier()
            intent = classifier.classify(html, subject=subject)
            injector = SchemaMarkupInjector()
            result = injector.inject(html, intent)
            result_dict = to_dict(result)
            return format_simple_result(
                {
                    "intent": result_dict.get("intent_type", str(intent.intent_type)),
                    "html": truncate_html(result_dict.get("html", "")),
                },
                "Schema Markup Injection",
            )
        except Exception:
            logger.exception("mcp.tool_error", tool="inject_schema_markup")
            return "Schema markup injection failed due to an internal error."
