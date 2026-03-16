# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false
# ruff: noqa: ANN401, ARG002
"""Visual QA agent service — VLM-powered screenshot analysis."""

from __future__ import annotations

import json
from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.agents.visual_qa.decisions import DetectedDefect, VisualQADecisions
from app.ai.agents.visual_qa.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.visual_qa.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.visual_qa.schemas import VisualDefect, VisualQARequest, VisualQAResponse
from app.core.logging import get_logger
from app.qa_engine.schemas import QACheckResult

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
        self, relevant_skills: list[str], output_mode: str = "structured"
    ) -> str:
        return _build_system_prompt(relevant_skills, output_mode=output_mode)

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

    async def process(self, request: Any) -> VisualQAResponse:
        """Execute VLM analysis with multimodal input (screenshots + text).

        Overrides base process() because we need to send images as content blocks,
        not just text — the standard pipeline only handles text messages.
        """
        from app.ai.protocols import Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.ai.sanitize import sanitize_prompt
        from app.core.config import get_settings

        req: VisualQARequest = request
        settings = get_settings()

        # Validate screenshots
        for client, b64 in req.screenshots.items():
            if len(b64) > _MAX_SCREENSHOT_B64_LEN:
                logger.warning("agents.visual_qa.screenshot_too_large", client=client)
                return VisualQAResponse(
                    summary=f"Screenshot for {client} exceeds size limit",
                    model="",
                )

        # Resolve VLM model (uses visual_qa-specific model if configured)
        visual_qa_model = settings.ai.visual_qa_model
        if visual_qa_model:
            model = visual_qa_model
        else:
            model = resolve_model(self.model_tier)
        provider_name = settings.ai.provider
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills)

        # Build multimodal user message with screenshot images
        text_content = sanitize_prompt(self._build_user_message(request))

        # Build content blocks: text + images
        content_blocks: list[dict[str, Any]] = [
            {"type": "text", "text": text_content},
        ]
        for client_name, b64_data in req.screenshots.items():
            content_blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64_data,
                    },
                }
            )
            # Add client label after each image
            content_blocks.append(
                {
                    "type": "text",
                    "text": f"[Screenshot: {client_name}]",
                }
            )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=content_blocks),  # type: ignore[arg-type]
        ]

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


# ── Module-level singleton ──

_visual_qa_service: VisualQAService | None = None


def get_visual_qa_service() -> VisualQAService:
    """Get or create the visual QA service singleton."""
    global _visual_qa_service
    if _visual_qa_service is None:
        _visual_qa_service = VisualQAService()
    return _visual_qa_service
