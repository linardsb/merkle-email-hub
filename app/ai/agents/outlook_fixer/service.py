# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Outlook Fixer agent service — fixes Outlook rendering issues in email HTML."""

from collections.abc import AsyncIterator
from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.agents.outlook_fixer.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.outlook_fixer.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.outlook_fixer.schemas import (
    OutlookFixerRequest,
    OutlookFixerResponse,
)
from app.qa_engine.schemas import QACheckResult


class OutlookFixerService(BaseAgentService):
    """Orchestrates the Outlook Fixer agent pipeline.

    Pipeline: detect skills → build prompt → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    agent_name = "outlook_fixer"
    model_tier = "standard"
    stream_prefix = "outlook-fix"

    def build_system_prompt(self, relevant_skills: list[str]) -> str:
        return _build_system_prompt(relevant_skills)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: OutlookFixerRequest = request
        return _detect_relevant_skills(req.html, req.issues)

    def _build_user_message(self, request: Any) -> str:
        req: OutlookFixerRequest = request
        parts: list[str] = [
            "Fix the following email HTML for Outlook desktop compatibility:\n",
            req.html,
        ]
        if req.issues:
            issues_str = ", ".join(req.issues)
            parts.append(f"\n\nSpecific issues to address: {issues_str}")
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
    ) -> OutlookFixerResponse:
        return OutlookFixerResponse(
            html=html,
            fixes_applied=skills_loaded,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
            confidence=confidence,
            skills_loaded=skills_loaded,
        )

    async def stream_process(self, request: Any) -> AsyncIterator[str]:
        async for chunk in super().stream_process(request):
            yield chunk


# ── Module-level singleton ──

_outlook_fixer_service: OutlookFixerService | None = None


def get_outlook_fixer_service() -> OutlookFixerService:
    """Get or create the Outlook Fixer service singleton."""
    global _outlook_fixer_service
    if _outlook_fixer_service is None:
        _outlook_fixer_service = OutlookFixerService()
    return _outlook_fixer_service
