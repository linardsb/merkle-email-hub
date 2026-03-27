# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401, ARG002
"""Accessibility Auditor agent service — audits and fixes WCAG issues in email HTML."""

from __future__ import annotations

import contextvars
import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai.multimodal import ContentBlock

from app.ai.agents.accessibility.alt_text_validator import format_alt_text_warnings
from app.ai.agents.accessibility.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.accessibility.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.accessibility.schemas import (
    AccessibilityRequest,
    AccessibilityResponse,
)
from app.ai.agents.base import BaseAgentService
from app.ai.agents.schemas.accessibility_decisions import (
    AccessibilityDecisions,
    AltTextDecision,
    HeadingDecision,
)
from app.core.logging import get_logger
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

# Per-request storage for alt text warnings (avoids race on singleton instance)
_alt_text_warnings_var: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "a11y_alt_text_warnings", default=None
)


class AccessibilityService(BaseAgentService):
    """Orchestrates the Accessibility Auditor agent pipeline.

    Pipeline: detect skills → build prompt → LLM call → validate output →
    extract HTML → XSS sanitize → alt text validation → optional QA checks.
    """

    agent_name = "accessibility"
    sanitization_profile = "accessibility"
    model_tier = "standard"
    stream_prefix = "a11y-fix"
    _output_mode_supported: bool = True

    def _post_process(self, raw_content: str) -> str:
        """Post-process LLM output: extract HTML, sanitize, then validate alt text quality."""
        html = super()._post_process(raw_content)
        warnings = format_alt_text_warnings(html)
        _alt_text_warnings_var.set(warnings)
        if warnings:
            logger.warning(
                "agents.accessibility.alt_text_validation_issues",
                issue_count=len(warnings),
                issues=warnings[:10],
            )
        return html

    def build_system_prompt(
        self,
        relevant_skills: list[str],
        output_mode: str = "html",
        *,
        client_id: str | None = None,
    ) -> str:
        return _build_system_prompt(relevant_skills, output_mode=output_mode, client_id=client_id)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: AccessibilityRequest = request
        return _detect_relevant_skills(req.html, req.focus_areas)

    def _build_user_message(self, request: Any) -> str:
        req: AccessibilityRequest = request
        parts: list[str] = [
            "Audit and fix the following email HTML for WCAG 2.1 AA accessibility:\n",
            req.html,
        ]
        if req.focus_areas:
            areas_str = ", ".join(req.focus_areas)
            parts.append(f"\n\nFocus on these areas: {areas_str}")
        return "\n".join(parts)

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
    ) -> AccessibilityResponse:
        return AccessibilityResponse(
            html=html,
            skills_loaded=skills_loaded,
            alt_text_warnings=_alt_text_warnings_var.get(None) or [],
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
            confidence=confidence,
        )

    async def _process_structured(self, request: Any) -> AccessibilityResponse:
        """Structured mode: analyze plan and return accessibility decisions."""
        from app.ai.protocols import Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.ai.sanitize import sanitize_prompt
        from app.core.config import get_settings

        req: AccessibilityRequest = request
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self.model_tier)
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills, output_mode="structured")

        plan_data = req.build_plan or {}
        user_message = (
            "Analyze the following EmailBuildPlan and return accessibility decisions as JSON.\n\n"
            f"Plan: {json.dumps(plan_data, default=str)}\n\n"
            "Return a JSON object with:\n"
            "- alt_texts: array of {slot_id, alt_text, is_decorative}\n"
            "- heading_fixes: array of {slot_id, current_level, recommended_level, reason}\n"
            "- lang_attribute: string\n"
            "- confidence: float 0-1\n"
            "- reasoning: string"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        registry = get_registry()
        provider = registry.get_llm(provider_name)
        result = await provider.complete(messages, model_override=model, max_tokens=self.max_tokens)

        decisions = self._parse_accessibility_decisions(result.content)

        logger.info(
            "agents.accessibility.structured_completed",
            alt_texts=len(decisions.alt_texts),
            heading_fixes=len(decisions.heading_fixes),
            confidence=decisions.confidence,
        )

        return AccessibilityResponse(
            html="",
            model=model_id,
            confidence=decisions.confidence,
            skills_loaded=relevant_skills,
            alt_text_warnings=[],
            decisions=decisions,
        )

    def _parse_accessibility_decisions(self, raw_content: str) -> AccessibilityDecisions:
        """Parse LLM response into AccessibilityDecisions."""
        content = raw_content.strip()
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
            logger.warning("agents.accessibility.structured_parse_failed")
            return AccessibilityDecisions(confidence=0.0, reasoning="Failed to parse LLM response")

        alt_texts = tuple(
            AltTextDecision(
                slot_id=str(a.get("slot_id", "")),
                alt_text=str(a.get("alt_text", "")),
                is_decorative=bool(a.get("is_decorative", False)),
            )
            for a in data.get("alt_texts", [])
            if isinstance(a, dict)
        )

        heading_fixes = tuple(
            HeadingDecision(
                slot_id=str(h.get("slot_id", "")),
                current_level=int(h.get("current_level", 1)),
                recommended_level=int(h.get("recommended_level", 1)),
                reason=str(h.get("reason", "")),
            )
            for h in data.get("heading_fixes", [])
            if isinstance(h, dict)
        )

        return AccessibilityDecisions(
            alt_texts=alt_texts,
            heading_fixes=heading_fixes,
            lang_attribute=str(data.get("lang_attribute", "en")),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )

    async def stream_process(
        self, request: Any, context_blocks: list[ContentBlock] | None = None
    ) -> AsyncIterator[str]:
        async for chunk in super().stream_process(request, context_blocks):
            yield chunk


# ── Module-level singleton ──

_accessibility_service: AccessibilityService | None = None


def get_accessibility_service() -> AccessibilityService:
    """Get or create the Accessibility service singleton."""
    global _accessibility_service
    if _accessibility_service is None:
        _accessibility_service = AccessibilityService()
    return _accessibility_service
