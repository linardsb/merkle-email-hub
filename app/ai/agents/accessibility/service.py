# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Accessibility Auditor agent service — audits and fixes WCAG issues in email HTML."""

from collections.abc import AsyncIterator
from typing import Any

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
from app.qa_engine.schemas import QACheckResult


class AccessibilityService(BaseAgentService):
    """Orchestrates the Accessibility Auditor agent pipeline.

    Pipeline: detect skills → build prompt → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    agent_name = "accessibility"
    model_tier = "standard"
    stream_prefix = "a11y-fix"

    def build_system_prompt(self, relevant_skills: list[str]) -> str:
        return _build_system_prompt(relevant_skills)

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
