# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Scaffolder agent service — orchestrates LLM → extract → sanitize → QA."""

from collections.abc import AsyncIterator
from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.agents.scaffolder.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.scaffolder.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.scaffolder.schemas import ScaffolderRequest, ScaffolderResponse
from app.qa_engine.schemas import QACheckResult


class ScaffolderService(BaseAgentService):
    """Orchestrates the scaffolder agent pipeline.

    Pipeline: build messages → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    agent_name = "scaffolder"
    model_tier = "complex"
    stream_prefix = "scaffold"

    def build_system_prompt(self, relevant_skills: list[str]) -> str:
        return _build_system_prompt(relevant_skills)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: ScaffolderRequest = request
        return _detect_relevant_skills(req.brief)

    def _build_user_message(self, request: Any) -> str:
        req: ScaffolderRequest = request
        return req.brief

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
    ) -> ScaffolderResponse:
        return ScaffolderResponse(
            html=html,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
            confidence=confidence,
            skills_loaded=skills_loaded,
        )

    # Scaffolder uses generate/stream_generate names for backward compat with routes
    async def generate(self, request: ScaffolderRequest) -> ScaffolderResponse:
        """Generate email HTML from a campaign brief."""
        return await self.process(request)  # type: ignore[no-any-return]

    async def stream_generate(self, request: ScaffolderRequest) -> AsyncIterator[str]:
        """Stream email HTML generation as SSE-formatted chunks."""
        async for chunk in self.stream_process(request):
            yield chunk


# ── Module-level singleton ──

_scaffolder_service: ScaffolderService | None = None


def get_scaffolder_service() -> ScaffolderService:
    """Get or create the scaffolder service singleton."""
    global _scaffolder_service
    if _scaffolder_service is None:
        _scaffolder_service = ScaffolderService()
    return _scaffolder_service
