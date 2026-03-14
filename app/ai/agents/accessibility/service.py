# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Accessibility Auditor agent service — audits and fixes WCAG issues in email HTML."""

import contextvars
from collections.abc import AsyncIterator
from typing import Any

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
    model_tier = "standard"
    stream_prefix = "a11y-fix"

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

    def build_system_prompt(self, relevant_skills: list[str], output_mode: str = "html") -> str:
        return _build_system_prompt(relevant_skills, output_mode=output_mode)

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

    async def stream_process(self, request: Any) -> AsyncIterator[str]:
        async for chunk in super().stream_process(request):
            yield chunk


# ── Module-level singleton ──

_accessibility_service: AccessibilityService | None = None


def get_accessibility_service() -> AccessibilityService:
    """Get or create the Accessibility service singleton."""
    global _accessibility_service
    if _accessibility_service is None:
        _accessibility_service = AccessibilityService()
    return _accessibility_service
