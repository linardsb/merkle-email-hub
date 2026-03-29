# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Visual Precheck deterministic node — pre-QA VLM-based screenshot analysis.

Feature-gated behind BLUEPRINT__VISUAL_QA_PRECHECK (default: off).
Renders the current HTML for top N target clients, runs lightweight VLM
defect detection, and converts detected defects to StructuredFailure objects
for the recovery router.
"""

from __future__ import annotations

from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType, StructuredFailure
from app.core.logging import get_logger

logger = get_logger(__name__)


class VisualPrecheckNode:
    """Pre-QA visual check via VLM screenshots.

    Renders the current HTML for the audience's top clients, runs
    lightweight defect detection, and returns StructuredFailure objects.
    Screenshots are stored in metadata for downstream multimodal injection.
    """

    @property
    def name(self) -> str:
        return "visual_precheck"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Render screenshots and detect visual defects via VLM."""
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.blueprint.visual_qa_precheck:
            return NodeResult(
                status="skipped", html=context.html, details="visual_qa_precheck disabled"
            )

        if not context.html:
            return NodeResult(status="skipped", html=context.html, details="no HTML to check")

        # Extract target client IDs from audience profile
        audience = context.metadata.get("audience_profile", {}) if context.metadata else {}
        client_ids: list[str] = []
        if isinstance(audience, dict):
            client_ids = list(audience.get("client_ids", []))
        if not client_ids:
            # Fallback defaults
            client_ids = ["gmail_web", "outlook_2019", "apple_mail"]

        top_n = settings.blueprint.visual_precheck_top_clients
        client_ids = client_ids[:top_n]

        # Render screenshots
        try:
            screenshots = await self._render_screenshots(context.html, client_ids)
        except Exception:
            logger.warning("blueprint.visual_precheck.render_failed", exc_info=True)
            return NodeResult(
                status="skipped", html=context.html, details="screenshot rendering failed"
            )

        if not screenshots:
            return NodeResult(
                status="skipped", html=context.html, details="no screenshots generated"
            )

        # Store screenshots for downstream multimodal injection
        if context.metadata is not None:
            context.metadata["precheck_screenshots"] = screenshots

        # Run lightweight VLM defect detection
        try:
            from app.ai.agents.visual_qa.service import get_visual_qa_service

            service = get_visual_qa_service()
            defects = await service.detect_defects_lightweight(screenshots, context.html)
        except Exception:
            logger.warning("blueprint.visual_precheck.vlm_failed", exc_info=True)
            return NodeResult(status="skipped", html=context.html, details="VLM detection failed")

        if not defects:
            logger.info("blueprint.visual_precheck.no_defects", clients=len(client_ids))
            return NodeResult(
                status="success",
                html=context.html,
                details=f"Visual precheck passed ({len(client_ids)} clients)",
            )

        # Convert to StructuredFailure objects (high/critical only trigger recovery)
        structured_failures: list[StructuredFailure] = []
        for defect in defects:
            if defect.severity in ("high", "critical"):
                structured_failures.append(
                    StructuredFailure(
                        check_name=f"visual_defect:{defect.client_id}",
                        score=0.0 if defect.severity == "critical" else 0.3,
                        details=defect.description,
                        suggested_agent=defect.suggested_agent or "scaffolder",
                        priority=0,  # Highest priority
                        severity=defect.severity,
                    )
                )

        # Also store failures in metadata for QA gate merge
        if context.metadata is not None:
            context.metadata["visual_precheck_failures"] = [
                {
                    "check_name": f.check_name,
                    "score": f.score,
                    "details": f.details,
                    "suggested_agent": f.suggested_agent,
                    "priority": f.priority,
                    "severity": f.severity,
                }
                for f in structured_failures
            ]

        if structured_failures:
            summary = "; ".join(f"{f.check_name}: {f.details}" for f in structured_failures)
            logger.info(
                "blueprint.visual_precheck.defects_found",
                total=len(defects),
                actionable=len(structured_failures),
            )
            return NodeResult(
                status="failed",
                html=context.html,
                details=summary,
                structured_failures=tuple(structured_failures),
            )

        logger.info(
            "blueprint.visual_precheck.low_severity_only",
            total=len(defects),
        )
        return NodeResult(
            status="success",
            html=context.html,
            details=f"Visual precheck: {len(defects)} low-severity defects (no action needed)",
        )

    async def _render_screenshots(self, html: str, client_ids: list[str]) -> dict[str, str]:
        """Render HTML for target clients and return base64 PNG dict."""
        import base64

        from app.rendering.local.service import LocalRenderingProvider

        renderer = LocalRenderingProvider()
        render_results = await renderer.render_screenshots(html, client_ids)

        screenshots: dict[str, str] = {}
        for item in render_results:
            client = str(item.get("client_name", ""))
            image_bytes = item.get("image_bytes", b"")
            if client and image_bytes:
                screenshots[client] = base64.b64encode(
                    image_bytes if isinstance(image_bytes, bytes) else b""
                ).decode()
        return screenshots
