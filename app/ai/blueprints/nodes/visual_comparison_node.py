# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Visual Comparison deterministic node — post-build screenshot comparison.

Feature-gated behind BLUEPRINT__VISUAL_COMPARISON (default: off).
Compares rendered email screenshots against the original design and/or
previous iteration. Advisory only — never blocks output.
"""

from __future__ import annotations

from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.core.logging import get_logger

logger = get_logger(__name__)


class VisualComparisonNode:
    """Post-build screenshot comparison against original design.

    Uses ODiff for pixel diff + VLM for semantic interpretation.
    Advisory only — stores result in metadata but never returns "failed".
    """

    @property
    def name(self) -> str:
        return "visual_comparison"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Compare rendered screenshots against original design."""
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.blueprint.visual_comparison:
            return NodeResult(
                status="skipped", html=context.html, details="visual_comparison disabled"
            )

        if not context.html:
            return NodeResult(status="skipped", html=context.html, details="no HTML")

        metadata = context.metadata or {}
        _raw_orig = metadata.get("original_screenshots", {})
        original_screenshots: dict[str, str] = (
            dict(_raw_orig) if isinstance(_raw_orig, dict) else {}
        )
        if not original_screenshots:
            return NodeResult(
                status="skipped",
                html=context.html,
                details="no original design screenshots available",
            )

        # Get current rendered screenshots (from precheck or render fresh)
        _raw_current = metadata.get("precheck_screenshots", metadata.get("screenshots", {}))
        current_screenshots: dict[str, str] = (
            dict(_raw_current) if isinstance(_raw_current, dict) else {}
        )
        if not current_screenshots:
            try:
                current_screenshots = await self._render_current(context.html, original_screenshots)
            except Exception:
                logger.warning("blueprint.visual_comparison.render_failed", exc_info=True)
                return NodeResult(
                    status="skipped",
                    html=context.html,
                    details="failed to render current screenshots",
                )

        if not current_screenshots:
            return NodeResult(
                status="skipped",
                html=context.html,
                details="no current screenshots for comparison",
            )

        # Run comparison
        threshold = settings.blueprint.visual_comparison_threshold
        try:
            from app.ai.agents.visual_qa.service import get_visual_qa_service

            service = get_visual_qa_service()
            result = await service.compare_screenshots(
                original=original_screenshots,
                rendered=current_screenshots,
                threshold=threshold,
            )
        except Exception:
            logger.warning("blueprint.visual_comparison.compare_failed", exc_info=True)
            return NodeResult(
                status="skipped",
                html=context.html,
                details="screenshot comparison failed",
            )

        # Check for regression vs previous iteration
        if context.iteration > 0:
            _raw_prev = metadata.get("prev_screenshots", {})
            prev_screenshots: dict[str, str] = (
                dict(_raw_prev) if isinstance(_raw_prev, dict) else {}
            )
            if prev_screenshots:
                try:
                    prev_result = await service.compare_screenshots(
                        original=original_screenshots,
                        rendered=prev_screenshots,
                        threshold=threshold,
                    )
                    if result.drift_score > prev_result.drift_score:
                        result = result.model_copy(update={"regressed": True})
                except Exception:
                    logger.warning(
                        "blueprint.visual_comparison.regression_check_failed", exc_info=True
                    )

        # Store result in metadata for BuildResponse
        if context.metadata is not None:
            context.metadata["visual_comparison"] = result.model_dump()
            # Save current screenshots as prev for next iteration
            context.metadata["prev_screenshots"] = current_screenshots

        drift_detail = f"drift_score={result.drift_score:.1f}%"
        if result.regressed:
            drift_detail += " (REGRESSED vs previous iteration)"
        if result.semantic_description:
            drift_detail += f" — {result.semantic_description}"

        logger.info(
            "blueprint.visual_comparison.completed",
            drift_score=result.drift_score,
            regressed=result.regressed,
        )
        return NodeResult(
            status="success",
            html=context.html,
            details=drift_detail,
        )

    async def _render_current(self, html: str, original: dict[str, str]) -> dict[str, str]:
        """Render HTML for the same clients as the original screenshots."""
        import base64

        from app.rendering.local.service import LocalRenderingProvider

        renderer = LocalRenderingProvider()
        client_ids = list(original.keys())
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
