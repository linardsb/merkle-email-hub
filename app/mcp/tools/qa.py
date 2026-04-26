"""QA & quality analysis tools for email HTML."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.core.logging import get_logger
from app.mcp import MCPContext
from app.mcp.auth import require_scope
from app.mcp.formatting import format_qa_result, format_simple_result, to_dict, truncate_html

logger = get_logger(__name__)

_MAX_HTML_SIZE = 500_000  # 500KB — matches QARunRequest.html max_length


def _validate_html(html: str) -> str | None:
    """Return error message if HTML is invalid, None if OK."""
    if not html.strip():
        return "HTML input is empty."
    if len(html) > _MAX_HTML_SIZE:
        return f"HTML too large ({len(html):,} chars). Maximum is {_MAX_HTML_SIZE:,} chars."
    return None


def register_qa_tools(mcp: FastMCP) -> None:
    """Register all QA-domain tools on the MCP server."""

    @mcp.tool()
    @require_scope("read")
    async def qa_check(
        html: str,
        ctx: MCPContext,
        target_clients: list[str] | None = None,
        skip_checks: list[str] | None = None,
    ) -> str:
        """Validate HTML email against 11 quality gates: HTML structure, CSS client support \
(Gmail strips <style> tags, Outlook uses Word rendering engine), file size (Gmail clips \
at 102KB), link integrity, spam score triggers, dark mode compatibility, WCAG AA \
accessibility, MSO conditional fallbacks for Outlook, image optimization (dimensions, \
alt text, file size), brand compliance, and personalization syntax (Handlebars/Liquid/AMPscript).

Returns per-check pass/fail with severity levels and actionable fix suggestions. \
Use this as the first step before sending any email to production.

Output: Markdown report with overall score, failed checks with fixes, and recommended next steps."""
        if err := _validate_html(html):
            return err
        try:
            from app.core.database import get_db_context
            from app.qa_engine.schemas import QARunRequest
            from app.qa_engine.service import QAEngineService

            async with get_db_context() as db:
                service = QAEngineService(db)
                request = QARunRequest(html=html)  # pyright: ignore[reportCallIssue]
                result = await service.run_checks(request)
            return format_qa_result(to_dict(result))
        except Exception:
            logger.exception("mcp.tool_error", tool="qa_check")
            return "QA check failed due to an internal error. Please try again."

    @mcp.tool()
    @require_scope("read")
    async def email_production_readiness(
        html: str,
        ctx: MCPContext,
        subject: str = "",
        from_name: str = "Sender",
    ) -> str:
        """Comprehensive pre-send analysis combining 4 checks into a single production readiness \
report: (1) Full QA gate (11 checks), (2) Deliverability prediction score (content quality, \
HTML hygiene, auth readiness, engagement signals — scored 0-100), (3) Gmail AI summary \
prediction (what Gemini will show as the email summary, promotional/transactional/social \
categorization), (4) Outlook Word engine dependency scan (VML shapes, ghost tables, MSO \
conditionals that may break in New Outlook).

This is the "can I ship this?" tool. Run it before any production send.

Output: Markdown report with go/no-go verdict, per-dimension scores, and prioritized fix list."""
        if err := _validate_html(html):
            return err
        try:
            await ctx.info("Running comprehensive production readiness analysis...")

            results: dict[str, Any] = {}

            # QA checks
            await ctx.report_progress(progress=0.2, total=1.0)
            from app.core.database import get_db_context
            from app.qa_engine.schemas import QARunRequest
            from app.qa_engine.service import QAEngineService

            async with get_db_context() as db:
                qa_service = QAEngineService(db)
                qa_result = await qa_service.run_checks(QARunRequest(html=html))  # pyright: ignore[reportCallIssue]
            results["qa"] = to_dict(qa_result)

            # Deliverability
            await ctx.report_progress(progress=0.4, total=1.0)
            from app.qa_engine.checks.deliverability import get_detailed_result

            score, passed, dimensions, _isp_analysis = get_detailed_result(html)
            results["deliverability"] = {
                "score": score,
                "passed": passed,
                "dimensions": [to_dict(d) for d in dimensions],
            }

            # Gmail prediction
            await ctx.report_progress(progress=0.6, total=1.0)
            try:
                from app.qa_engine.gmail_intelligence.predictor import GmailSummaryPredictor

                predictor = GmailSummaryPredictor()
                gmail_result = await predictor.predict(html, subject, from_name)
                results["gmail"] = to_dict(gmail_result)
            except Exception:
                logger.debug("mcp.gmail_prediction_skipped", reason="service_unavailable")
                results["gmail"] = {"status": "Gmail prediction unavailable"}

            # Outlook analysis
            await ctx.report_progress(progress=0.8, total=1.0)
            from app.qa_engine.outlook_analyzer.detector import OutlookDependencyDetector

            detector = OutlookDependencyDetector()
            results["outlook"] = to_dict(detector.analyze(html))

            await ctx.report_progress(progress=1.0, total=1.0)
            return _format_production_readiness(results)
        except Exception:
            logger.exception("mcp.tool_error", tool="email_production_readiness")
            return "Production readiness check failed due to an internal error."

    @mcp.tool()
    @require_scope("write")
    async def chaos_test(
        html: str,
        ctx: MCPContext,
        profiles: list[str] | None = None,
    ) -> str:
        """Stress-test email HTML against real-world client degradation scenarios. Simulates \
8 chaos profiles: Gmail style stripping (removes all <style> tags), image blocking \
(replaces images with alt text), dark mode color inversion, Outlook Word engine CSS \
limitations, Gmail clipping (102KB truncation), mobile narrow viewport (320px), \
CSS class stripping, and media query removal.

Each profile applies the degradation, then runs QA checks to measure resilience. \
Returns a resilience score (0-100) showing how well the email survives hostile conditions.

Use this after `qa_check` passes to verify the email degrades gracefully.

Output: Markdown with overall resilience score and per-profile pass/fail breakdown."""
        if err := _validate_html(html):
            return err
        try:
            from app.qa_engine.chaos.engine import ChaosEngine

            engine = ChaosEngine()
            result = await engine.run_chaos_test(html, profiles=profiles)
            return format_simple_result(to_dict(result), "Chaos Test")
        except Exception:
            logger.exception("mcp.tool_error", tool="chaos_test")
            return "Chaos test failed due to an internal error."

    @mcp.tool()
    @require_scope("read")
    async def outlook_analyze(
        html: str,
        ctx: MCPContext,
        target: str = "dual_support",
    ) -> str:
        """Detect Outlook Word rendering engine dependencies in HTML email and suggest \
modernization paths. Scans for 7 dependency types: VML shapes, ghost tables, MSO \
conditionals (<!--[if mso]>), MSO-specific CSS properties (mso-line-height-rule, etc.), \
DPI-dependent images, .ExternalClass hacks, and word-wrap workarounds.

Target modes: 'new_outlook' (aggressive removal for New Outlook only), \
'dual_support' (keep conditionals for backward compat), 'audit_only' (report without changes).

Output: Dependency list with severity, modernization recommendations, and optionally \
cleaned HTML."""
        if err := _validate_html(html):
            return err
        try:
            from app.qa_engine.outlook_analyzer.detector import OutlookDependencyDetector
            from app.qa_engine.outlook_analyzer.modernizer import OutlookModernizer

            detector = OutlookDependencyDetector()
            analysis = detector.analyze(html)

            if target != "audit_only":
                modernizer = OutlookModernizer()
                modernized = modernizer.modernize(html, analysis, target=target)
                return format_simple_result(
                    {
                        "analysis": to_dict(analysis),
                        "modernized_html": truncate_html(modernized.html),
                    },
                    "Outlook Analysis",
                )
            return format_simple_result(to_dict(analysis), "Outlook Analysis")
        except Exception:
            logger.exception("mcp.tool_error", tool="outlook_analyze")
            return "Outlook analysis failed due to an internal error."

    @mcp.tool()
    @require_scope("read")
    async def gmail_predict(
        html: str,
        ctx: MCPContext,
        subject: str = "",
        from_name: str = "Sender",
    ) -> str:
        """Predict how Gmail's AI (Gemini) will summarize this email and what tab/category \
it will land in (Primary, Promotions, Social, Updates). Analyzes promotional signals \
(discount language, urgency words, multiple CTAs), transactional signals (order numbers, \
tracking info), and social signals (user-generated content patterns).

Also predicts whether Gmail will clip the email (>102KB) and provides preview text \
optimization suggestions.

Output: Predicted summary, category with confidence, clipping risk, and optimization tips."""
        if err := _validate_html(html):
            return err
        try:
            from app.qa_engine.gmail_intelligence.predictor import GmailSummaryPredictor

            predictor = GmailSummaryPredictor()
            result = await predictor.predict(html, subject, from_name)
            return format_simple_result(to_dict(result), "Gmail Prediction")
        except Exception:
            logger.exception("mcp.tool_error", tool="gmail_predict")
            return "Gmail prediction failed due to an internal error."


def _format_production_readiness(results: dict[str, Any]) -> str:
    """Format combined production readiness report."""
    lines: list[str] = []

    qa_score = results.get("qa", {}).get("overall_score", 0)
    deliv_score = results.get("deliverability", {}).get("score", 0)
    outlook_deps = len(results.get("outlook", {}).get("dependencies", []))

    # Go/no-go verdict
    go = qa_score >= 85 and deliv_score >= 70
    verdict = "READY FOR PRODUCTION" if go else "NOT READY — fixes required"
    lines.append(f"## {verdict}")
    lines.append(f"- **QA Score:** {qa_score}/100")
    lines.append(f"- **Deliverability:** {deliv_score}/100")
    lines.append(f"- **Outlook Dependencies:** {outlook_deps}")
    lines.append("")

    # Detail sections
    lines.append("### QA Results")
    lines.append(format_qa_result(results.get("qa", {})))
    lines.append("")
    lines.append("### Deliverability")
    lines.append(format_simple_result(results.get("deliverability", {}), "Deliverability"))

    if gmail := results.get("gmail"):
        lines.append("\n### Gmail Prediction")
        lines.append(format_simple_result(gmail, "Gmail"))

    if outlook_deps > 0:
        lines.append("\n### Outlook Dependencies")
        lines.append(format_simple_result(results.get("outlook", {}), "Outlook"))

    return "\n".join(lines)
