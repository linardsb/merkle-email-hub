# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false
# ruff: noqa: ANN401, ARG002
"""Visual QA agent service — VLM-powered screenshot analysis."""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai.multimodal import ContentBlock

from app.ai.agents.base import BaseAgentService
from app.ai.agents.visual_qa.decisions import DetectedDefect, VisualQADecisions
from app.ai.agents.visual_qa.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.visual_qa.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.visual_qa.schemas import (
    VisualComparisonResult,
    VisualDefect,
    VisualQARequest,
    VisualQAResponse,
)
from app.core.logging import get_logger
from app.qa_engine.schemas import QACheckResult, QAVisualDefect

logger = get_logger(__name__)

# Max base64 size per screenshot (10MB — generous for PNGs)
_MAX_SCREENSHOT_B64_LEN = 14_000_000


class VisualQAService(BaseAgentService):
    """Orchestrates VLM-based visual analysis of email screenshots.

    Pipeline: build multimodal messages → VLM call → parse structured defects
    → cross-reference ontology → return VisualQAResponse.

    This is an advisory/analysis agent — it does NOT modify HTML.
    """

    agent_name = "visual_qa"
    model_tier = "standard"  # VLM calls need capable models
    stream_prefix = "visualqa"
    _output_mode_supported: bool = False  # Always structured output

    def build_system_prompt(
        self,
        relevant_skills: list[str],
        output_mode: str = "structured",
        *,
        client_id: str | None = None,
    ) -> str:
        return _build_system_prompt(relevant_skills, output_mode=output_mode, client_id=client_id)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: VisualQARequest = request
        return _detect_relevant_skills(req.html)

    def _build_user_message(self, request: Any) -> str:
        """Build text portion of user message (images added separately in process())."""
        req: VisualQARequest = request
        parts: list[str] = [
            f"Analyze these email screenshots rendered across {len(req.screenshots)} clients.\n",
            f"Clients: {', '.join(req.screenshots.keys())}\n",
        ]
        # Include HTML structure summary (truncated for context window)
        html_preview = req.html[:3000] if len(req.html) > 3000 else req.html
        parts.append(f"\nOriginal HTML (first 3000 chars):\n```html\n{html_preview}\n```")

        if req.baseline_diffs:
            parts.append("\nODiff pixel comparison results:")
            for diff in req.baseline_diffs:
                parts.append(
                    f"  - {diff.get('client', '?')}: {diff.get('diff_percentage', '?')}% changed, "
                    f"{diff.get('changed_pixels', '?')} pixels"
                )

        parts.append(
            "\nReturn your analysis as JSON. Focus on defects that would affect "
            "the email's usability, readability, or brand presentation."
        )
        return "\n".join(parts)

    def _screenshots_to_blocks(
        self, screenshots: dict[str, str]
    ) -> list[ContentBlock] | VisualQAResponse:
        """Convert base64 screenshot dict to validated ImageBlock list.

        Returns list[ContentBlock] on success, or VisualQAResponse on error.
        """
        from app.ai.multimodal import TextBlock

        blocks: list[ContentBlock] = []
        for client_name, b64_data in screenshots.items():
            if len(b64_data) > _MAX_SCREENSHOT_B64_LEN:
                logger.warning("agents.visual_qa.screenshot_too_large", client=client_name)
                return VisualQAResponse(
                    summary=f"Screenshot for {client_name} exceeds size limit",
                    model="",
                )
            try:
                image_bytes = base64.b64decode(b64_data)
            except Exception:
                logger.warning("agents.visual_qa.invalid_base64", client=client_name, exc_info=True)
                return VisualQAResponse(
                    summary=f"Invalid base64 data for screenshot {client_name}",
                    model="",
                )
            blocks.append(self._image_block(image_bytes, "image/png"))
            blocks.append(TextBlock(text=f"[Screenshot: {client_name}]"))
        return blocks

    async def process(
        self, request: Any, context_blocks: list[ContentBlock] | None = None
    ) -> VisualQAResponse:
        """Execute VLM analysis with multimodal input (screenshots + text).

        Overrides base process() because we need to send images as content blocks,
        not just text — the standard pipeline only handles text messages.
        """
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.core.config import get_settings

        req: VisualQARequest = request
        settings = get_settings()

        # Validate and convert screenshots to ImageBlocks
        image_blocks = self._screenshots_to_blocks(req.screenshots)
        if isinstance(image_blocks, VisualQAResponse):
            return image_blocks  # Error response

        # Resolve VLM model (uses visual_qa-specific model if configured)
        visual_qa_model = settings.ai.visual_qa_model
        model = visual_qa_model or resolve_model(self.model_tier)
        provider_name = settings.ai.provider
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills)

        # Build multimodal messages using base class helper
        user_text = self._build_user_message(request)
        messages = self._build_multimodal_messages(
            system_prompt=system_prompt,
            user_text=user_text,
            context_blocks=image_blocks,
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=4096)
        except Exception as exc:
            logger.error("agents.visual_qa.llm_failed", error=str(exc))
            return VisualQAResponse(
                summary="VLM analysis failed — check logs for details",
                model=model_id,
            )

        # Parse structured response
        decisions = self.parse_decisions(result.content)

        # Cross-reference with ontology for known fallbacks
        decisions = self.enrich_with_ontology(decisions)

        logger.info(
            "agents.visual_qa.completed",
            defects=len(decisions.defects),
            score=decisions.overall_rendering_score,
            confidence=decisions.confidence,
        )

        # Convert decisions to response
        defects = [
            VisualDefect(
                region=d.region,
                description=d.description,
                severity=d.severity,
                affected_clients=list(d.affected_clients),
                suggested_fix=d.suggested_fix,
                css_property=d.css_property or None,
            )
            for d in decisions.defects
        ]

        return VisualQAResponse(
            defects=defects,
            summary=decisions.summary,
            overall_rendering_score=decisions.overall_rendering_score,
            auto_fixable=decisions.auto_fixable,
            critical_clients=list(decisions.critical_clients),
            model=model_id,
            confidence=decisions.confidence,
            skills_loaded=relevant_skills,
        )

    def parse_decisions(self, raw_content: str) -> VisualQADecisions:
        """Parse VLM response into VisualQADecisions."""
        content = raw_content.strip()
        # Extract JSON from code fence if present
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("agents.visual_qa.parse_failed")
            return VisualQADecisions(confidence=0.0, summary="Failed to parse VLM response")

        defects = tuple(
            DetectedDefect(
                region=str(d.get("region", "")),
                description=str(d.get("description", "")),
                severity=str(d.get("severity", "info")),
                affected_clients=tuple(d.get("affected_clients", [])),
                suggested_fix=str(d.get("suggested_fix", "")),
                css_property=str(d.get("css_property", "")),
            )
            for d in data.get("defects", [])
            if isinstance(d, dict)
        )

        try:
            score = float(data.get("overall_rendering_score", 1.0))
        except (ValueError, TypeError):
            score = 1.0
        try:
            confidence = float(data.get("confidence", 0.0))
        except (ValueError, TypeError):
            confidence = 0.0

        return VisualQADecisions(
            defects=defects,
            overall_rendering_score=score,
            critical_clients=tuple(data.get("critical_clients", [])),
            summary=str(data.get("summary", "")),
            confidence=confidence,
            auto_fixable=bool(data.get("auto_fixable", False)),
        )

    def enrich_with_ontology(self, decisions: VisualQADecisions) -> VisualQADecisions:
        """Cross-reference detected CSS issues with ontology for known fallbacks."""
        try:
            from app.knowledge.ontology import get_ontology

            ontology = get_ontology()
        except Exception:
            # Ontology not available — return as-is
            return decisions

        enriched_defects: list[DetectedDefect] = []
        for defect in decisions.defects:
            if not defect.css_property:
                enriched_defects.append(defect)
                continue

            # Look up property in ontology
            prop = ontology.find_property_by_name(defect.css_property)
            if prop is None:
                enriched_defects.append(defect)
                continue

            # Find fallbacks for this property
            fallbacks = ontology.fallbacks_for(prop.id)
            if fallbacks:
                fallback_text = "; ".join(
                    f"{fb.technique}: {fb.code_example}" for fb in fallbacks[:3]
                )
                enriched_fix = (
                    f"{defect.suggested_fix} [Ontology fallback: {fallback_text}]"
                ).strip()
                enriched_defects.append(
                    DetectedDefect(
                        region=defect.region,
                        description=defect.description,
                        severity=defect.severity,
                        affected_clients=defect.affected_clients,
                        suggested_fix=enriched_fix,
                        css_property=defect.css_property,
                    )
                )
            else:
                enriched_defects.append(defect)

        return VisualQADecisions(
            defects=tuple(enriched_defects),
            overall_rendering_score=decisions.overall_rendering_score,
            critical_clients=decisions.critical_clients,
            summary=decisions.summary,
            confidence=decisions.confidence,
            auto_fixable=decisions.auto_fixable,
        )

    async def detect_defects_lightweight(
        self,
        screenshots: dict[str, str],
        html: str,
    ) -> list[QAVisualDefect]:
        """Fast-path VLM defect detection for QA gate precheck.

        Uses a minimal prompt and lower max_tokens for speed.
        Returns QA-engine VisualDefect objects (not agent-level).
        """
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.core.config import get_settings

        settings = get_settings()

        # Validate screenshots
        image_blocks = self._screenshots_to_blocks(screenshots)
        if isinstance(image_blocks, VisualQAResponse):
            return []  # Validation error — skip silently

        visual_qa_model = settings.ai.visual_qa_model
        model = visual_qa_model or resolve_model(self.model_tier)
        provider_name = settings.ai.provider

        html_preview = html[:2000] if len(html) > 2000 else html
        user_text = (
            f"Detect rendering defects in these email screenshots.\n"
            f"Clients: {', '.join(screenshots.keys())}\n\n"
            f"HTML preview:\n```html\n{html_preview}\n```\n\n"
            "Return JSON with a 'defects' array only. Each defect: "
            '{"region", "description", "severity" (critical/warning/info), '
            '"affected_clients" (list), "suggested_fix"}.'
        )

        system_prompt = (
            "You are a visual QA specialist for HTML email. "
            "Detect rendering defects from screenshots. Be concise."
        )
        messages = self._build_multimodal_messages(
            system_prompt=system_prompt,
            user_text=user_text,
            context_blocks=image_blocks,
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=1024)
        except Exception as exc:
            logger.warning("agents.visual_qa.lightweight_detect_failed", error=str(exc))
            return []

        decisions = self.parse_decisions(result.content)

        qa_defects: list[QAVisualDefect] = []
        for d in decisions.defects:
            for client_id in d.affected_clients or list(screenshots.keys()):
                qa_defects.append(
                    QAVisualDefect(
                        type=d.region or "rendering_defect",
                        severity=_map_severity(d.severity),
                        client_id=client_id,
                        description=d.description,
                        suggested_agent=_infer_agent(d.suggested_fix, d.description),
                    )
                )

        logger.info(
            "agents.visual_qa.lightweight_detect_completed",
            defects_count=len(qa_defects),
        )
        return qa_defects

    async def compare_screenshots(
        self,
        original: dict[str, str],
        rendered: dict[str, str],
        threshold: float = 5.0,
    ) -> VisualComparisonResult:
        """Compare original design screenshots against rendered email.

        Uses ODiff for pixel diff, VLM for semantic interpretation when diff > threshold.
        """
        from app.rendering.visual_diff import compare_images

        max_drift: float = 0.0
        all_regions: list[dict[str, object]] = []
        clients_compared = 0

        for client_id in original:
            if client_id not in rendered:
                continue
            clients_compared += 1

            try:
                orig_bytes = base64.b64decode(original[client_id])
                rend_bytes = base64.b64decode(rendered[client_id])
            except Exception:
                logger.warning("agents.visual_qa.compare_decode_failed", client=client_id)
                continue

            try:
                diff_result = await compare_images(orig_bytes, rend_bytes)
            except Exception:
                logger.warning("agents.visual_qa.odiff_failed", client=client_id, exc_info=True)
                continue

            pct = diff_result.diff_percentage
            if pct > max_drift:
                max_drift = pct
            if pct > 0:
                all_regions.append(
                    {
                        "client": client_id,
                        "diff_percentage": pct,
                        "pixels": diff_result.pixel_count,
                    }
                )

        # VLM semantic description if drift exceeds threshold
        semantic = ""
        if max_drift > threshold and clients_compared > 0:
            semantic = await self._describe_drift(original, rendered, all_regions)

        logger.info(
            "agents.visual_qa.comparison_completed",
            drift_score=round(max_drift, 2),
            clients_compared=clients_compared,
        )
        return VisualComparisonResult(
            drift_score=round(max_drift, 2),
            diff_regions=all_regions,
            semantic_description=semantic,
        )

    async def _describe_drift(
        self,
        original: dict[str, str],
        rendered: dict[str, str],
        regions: list[dict[str, object]],
    ) -> str:
        """Ask VLM for a semantic description of visual differences."""
        from app.ai.multimodal import TextBlock
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.core.config import get_settings

        settings = get_settings()
        visual_qa_model = settings.ai.visual_qa_model
        model = visual_qa_model or resolve_model(self.model_tier)

        # Pick first client that has both original and rendered
        client_id = next((c for c in original if c in rendered), None)
        if client_id is None:
            return ""

        blocks: list[ContentBlock] = []
        try:
            orig_bytes = base64.b64decode(original[client_id])
            rend_bytes = base64.b64decode(rendered[client_id])
        except Exception:
            return ""

        blocks.append(self._image_block(orig_bytes, "image/png"))
        blocks.append(TextBlock(text="[Original design screenshot]"))
        blocks.append(self._image_block(rend_bytes, "image/png"))
        blocks.append(TextBlock(text="[Rendered email screenshot]"))

        region_summary = "; ".join(
            f"{r.get('client', '?')}: {r.get('diff_percentage', '?')}% changed" for r in regions[:5]
        )

        messages = self._build_multimodal_messages(
            system_prompt="Briefly describe the visual differences between the original design and rendered email.",
            user_text=(
                f"ODiff results: {region_summary}\n"
                "Describe the key visual differences in 1-2 sentences."
            ),
            context_blocks=blocks,
        )

        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        try:
            result = await provider.complete(messages, model_override=model, max_tokens=256)
            return result.content.strip()
        except Exception:
            logger.warning("agents.visual_qa.drift_describe_failed", exc_info=True)
            return ""

    def _build_response(
        self,
        *,
        request: Any,
        html: str,
        qa_results: list[QACheckResult] | None,
        qa_passed: bool | None,
        model_id: str,
        confidence: float | None,
        skills_loaded: list[str],
        raw_content: str,
    ) -> VisualQAResponse:
        """Not used — process() builds response directly."""
        return VisualQAResponse(model=model_id, skills_loaded=skills_loaded)


_SEVERITY_LITERAL = {"critical", "high", "medium", "low"}
_SEVERITY_MAP = {"warning": "medium", "info": "low"}


def _map_severity(severity_str: str) -> str:
    """Map VLM severity string to QA VisualDefect severity value."""
    s = severity_str.lower().strip()
    if s in _SEVERITY_LITERAL:
        return s
    return _SEVERITY_MAP.get(s, "medium")


def _infer_agent(suggested_fix: str, description: str) -> str | None:
    """Infer which fixer agent should handle a visual defect."""
    text = f"{suggested_fix} {description}".lower()
    if any(kw in text for kw in ("outlook", "vml", "ghost table", "mso")):
        return "outlook_fixer"
    if any(kw in text for kw in ("dark mode", "color-scheme", "prefers-color-scheme")):
        return "dark_mode"
    if any(kw in text for kw in ("contrast", "alt text", "accessibility", "aria", "wcag")):
        return "accessibility"
    return "scaffolder"


# ── Module-level singleton ──

_visual_qa_service: VisualQAService | None = None


def get_visual_qa_service() -> VisualQAService:
    """Get or create the visual QA service singleton."""
    global _visual_qa_service
    if _visual_qa_service is None:
        _visual_qa_service = VisualQAService()
    return _visual_qa_service
