# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Visual QA agentic node — VLM analysis of rendered email screenshots."""

from __future__ import annotations

import base64

from app.ai.agents.visual_qa.prompt import build_system_prompt, detect_relevant_skills
from app.ai.agents.visual_qa.service import (
    _MAX_SCREENSHOT_B64_LEN,
    VisualQAService,
    get_visual_qa_service,
)
from app.ai.blueprints.handoff import VisualQAHandoff
from app.ai.blueprints.protocols import (
    AgentHandoff,
    NodeContext,
    NodeResult,
    NodeType,
)
from app.ai.protocols import LLMProvider, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt
from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.local.service import LocalRenderingProvider

logger = get_logger(__name__)


class VisualQANode:
    """Agentic node that performs VLM-based visual analysis of email screenshots.

    Runs AFTER the export node as an optional validation step.
    When autofix is disabled (default): advisory only — does not modify HTML.
    When autofix is enabled: detects defects, applies LLM correction, re-renders to verify,
    and accepts the fix only if the rendering score improves.
    Defects always go into AgentHandoff.warnings regardless of autofix mode.
    Requires screenshots in context.metadata["screenshots"] (dict[str, str]: client → base64 PNG).
    """

    @property
    def name(self) -> str:
        return "visual_qa"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Analyze rendered screenshots via VLM."""
        settings = get_settings()

        # Check feature flag
        if not settings.ai.visual_qa_enabled:
            logger.info("blueprint.visual_qa_node.skipped", reason="feature_disabled")
            return NodeResult(
                status="skipped",
                html=context.html,
                details="Visual QA disabled via config",
            )

        # Get screenshots from context metadata (primary source)
        # LAYER 14 multimodal_context also available but screenshots dict
        # needed for auto-fix re-render path, so metadata remains canonical
        screenshots: dict[str, str] = context.metadata.get("screenshots", {})  # type: ignore[assignment]
        if not screenshots:
            logger.info("blueprint.visual_qa_node.skipped", reason="no_screenshots")
            return NodeResult(
                status="skipped",
                html=context.html,
                details="No screenshots available for visual analysis",
            )

        # Validate screenshot sizes
        for client, b64 in screenshots.items():
            if len(b64) > _MAX_SCREENSHOT_B64_LEN:
                logger.warning("blueprint.visual_qa_node.screenshot_too_large", client=client)
                return NodeResult(
                    status="failed",
                    html=context.html,
                    error=f"Screenshot for {client} exceeds size limit",
                )

        # Resolve VLM model
        visual_qa_model = settings.ai.visual_qa_model
        model = visual_qa_model or resolve_model("standard")
        provider_name = settings.ai.provider

        relevant_skills = detect_relevant_skills(context.html)
        system_prompt = build_system_prompt(relevant_skills)

        # Build multimodal message
        text_content = self._build_user_message(context, screenshots)

        from app.ai.multimodal import ContentBlock, ImageBlock, TextBlock

        blocks: list[ContentBlock] = [
            TextBlock(text=sanitize_prompt(text_content)),
        ]
        for client_name, b64_data in screenshots.items():
            blocks.append(
                ImageBlock(
                    data=base64.b64decode(b64_data),
                    media_type="image/png",
                    source="base64",
                )
            )
            blocks.append(TextBlock(text=f"[Screenshot: {client_name}]"))

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=blocks),
        ]

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            response = await provider.complete(messages, model_override=model, max_tokens=4096)
        except Exception as exc:
            logger.error("blueprint.visual_qa_node.llm_failed", error=str(exc))
            return NodeResult(
                status="failed",
                html=context.html,
                error="VLM call failed — check logs for details",
            )

        # Delegate parsing and enrichment to service (single source of truth)
        service = get_visual_qa_service()
        decisions = service.parse_decisions(response.content)
        decisions = service.enrich_with_ontology(decisions)

        usage = dict(response.usage) if response.usage else None

        # --- Phase 17.4: Auto-fix path ---
        corrected_html = context.html
        corrections_applied: list[str] = []
        verification_score: float | None = None

        if settings.ai.visual_qa_autofix_enabled and decisions.auto_fixable and decisions.defects:
            from app.ai.agents.visual_qa.correction import correct_visual_defects

            logger.info(
                "blueprint.visual_qa_node.autofix_started",
                defects=len(decisions.defects),
            )

            fixed_html, corrections_applied = await correct_visual_defects(
                context.html, decisions.defects, model
            )

            if corrections_applied:
                verification_score = await self._verify_fix(
                    fixed_html, screenshots, provider, model, system_prompt, service
                )

                if (
                    verification_score is not None
                    and verification_score > decisions.overall_rendering_score
                ):
                    corrected_html = fixed_html
                    logger.info(
                        "blueprint.visual_qa_node.autofix_accepted",
                        original_score=decisions.overall_rendering_score,
                        new_score=verification_score,
                        corrections=corrections_applied,
                    )
                else:
                    corrections_applied = []  # Reset — fix rejected
                    logger.info(
                        "blueprint.visual_qa_node.autofix_rejected",
                        original_score=decisions.overall_rendering_score,
                        verification_score=verification_score,
                        reason="no_improvement",
                    )

        # Build warnings from defects
        warnings = tuple(
            f"[{d.severity}] {d.region}: {d.description} (fix: {d.suggested_fix})"
            for d in decisions.defects
        )

        # Build typed handoff
        pre_fix_score = decisions.overall_rendering_score if corrections_applied else None
        typed = VisualQAHandoff(
            defects_found=len(decisions.defects),
            overall_score=verification_score
            if verification_score is not None and corrections_applied
            else decisions.overall_rendering_score,
            critical_clients=decisions.critical_clients,
            auto_fixable=decisions.auto_fixable,
            screenshotted_clients=tuple(screenshots.keys()),
            corrections_applied=tuple(corrections_applied),
            pre_fix_score=pre_fix_score,
        )

        handoff = AgentHandoff(
            agent_name="visual_qa",
            artifact="",  # Advisory — no HTML artifact
            decisions=(
                f"Visual QA: {len(decisions.defects)} defects found",
                f"Rendering score: {typed.overall_score:.2f}",
                f"Auto-fixable: {decisions.auto_fixable}",
            ),
            warnings=warnings,
            confidence=decisions.confidence,
            typed_payload=typed,
        )

        logger.info(
            "blueprint.visual_qa_node.completed",
            defects=len(decisions.defects),
            score=typed.overall_score,
            critical_clients=list(decisions.critical_clients),
            corrections=len(corrections_applied),
        )

        return NodeResult(
            status="success",
            html=corrected_html,
            details=f"Visual QA: {len(decisions.defects)} defects, score={typed.overall_score:.2f}"
            + (f", {len(corrections_applied)} auto-fixed" if corrections_applied else ""),
            usage=usage,
            handoff=handoff,
        )

    async def _verify_fix(
        self,
        fixed_html: str,
        original_screenshots: dict[str, str],
        provider: LLMProvider,
        model: str,
        system_prompt: str,
        service: VisualQAService,
    ) -> float | None:
        """Re-render fixed HTML and re-analyze to verify improvement.

        Returns the new rendering score, or None if verification failed.
        """
        try:
            renderer = LocalRenderingProvider()
            clients = list(original_screenshots.keys())
            render_results = await renderer.render_screenshots(fixed_html, clients)

            new_screenshots: dict[str, str] = {}
            for result in render_results:
                client_name = str(result["client_name"])
                image_bytes: bytes = result["image_bytes"]  # type: ignore[assignment]
                new_screenshots[client_name] = base64.b64encode(image_bytes).decode()

            if not new_screenshots:
                return None

            # Re-analyze with VLM (lightweight — just get the score)
            from app.ai.multimodal import ContentBlock, ImageBlock, TextBlock

            verify_blocks: list[ContentBlock] = [
                TextBlock(
                    text=sanitize_prompt(
                        f"Re-analyze these {len(new_screenshots)} screenshots after auto-fix. "
                        "Focus on whether the previous defects have been resolved. "
                        "Return JSON with: defects, overall_rendering_score, "
                        "critical_clients, summary, confidence, auto_fixable"
                    )
                ),
            ]
            for client_name, b64_data in new_screenshots.items():
                verify_blocks.append(
                    ImageBlock(
                        data=base64.b64decode(b64_data),
                        media_type="image/png",
                        source="base64",
                    )
                )
                verify_blocks.append(TextBlock(text=f"[Screenshot: {client_name}]"))

            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=verify_blocks),
            ]

            vlm_response = await provider.complete(messages, model_override=model, max_tokens=4096)
            verify_decisions = service.parse_decisions(vlm_response.content)
            return verify_decisions.overall_rendering_score

        except Exception:
            logger.warning("blueprint.visual_qa_node.verify_failed", exc_info=True)
            return None  # Verification failed — treat as no improvement

    def _build_user_message(self, context: NodeContext, screenshots: dict[str, str]) -> str:
        """Build text portion of the VLM prompt."""
        parts = [
            f"Analyze these {len(screenshots)} email screenshots for rendering defects.",
            f"Clients: {', '.join(screenshots.keys())}",
        ]
        # Include HTML summary
        html_preview = context.html[:3000] if len(context.html) > 3000 else context.html
        parts.append(f"\nOriginal HTML:\n```html\n{html_preview}\n```")

        # Include baseline diff data if available
        baseline_diffs: list[dict[str, object]] = context.metadata.get(  # type: ignore[assignment]
            "baseline_diffs", []
        )
        if baseline_diffs:
            parts.append("\nODiff pixel comparison results:")
            for diff in baseline_diffs:
                parts.append(
                    f"  - {diff.get('client', '?')}: {diff.get('diff_percentage', '?')}% changed"
                )

        parts.append(
            "\nReturn JSON with: defects, overall_rendering_score, "
            "critical_clients, summary, confidence, auto_fixable"
        )
        return "\n".join(parts)
