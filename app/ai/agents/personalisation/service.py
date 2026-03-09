# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Personalisation agent service -- injects ESP personalisation syntax into email HTML."""

from collections.abc import AsyncIterator
from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.agents.personalisation.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.personalisation.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.personalisation.schemas import (
    PersonalisationRequest,
    PersonalisationResponse,
)
from app.qa_engine.schemas import QACheckResult


class PersonalisationService(BaseAgentService):
    """Orchestrates the Personalisation agent pipeline.

    Pipeline: detect skills -> build prompt -> LLM call -> validate output ->
    extract HTML -> XSS sanitize -> optional QA checks.
    """

    agent_name = "personalisation"
    model_tier = "standard"
    stream_prefix = "personalise"

    def build_system_prompt(self, relevant_skills: list[str]) -> str:
        return _build_system_prompt(relevant_skills)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: PersonalisationRequest = request
        return _detect_relevant_skills(req.platform, req.requirements)

    def _build_user_message(self, request: Any) -> str:
        req: PersonalisationRequest = request
        return (
            f"Add personalisation to the following email HTML for the {req.platform} platform.\n\n"
            f"Requirements:\n{req.requirements}\n\n"
            f"Email HTML:\n{req.html}"
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
    ) -> PersonalisationResponse:
        req: PersonalisationRequest = request
        return PersonalisationResponse(
            html=html,
            platform=req.platform,
            tags_injected=skills_loaded,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
            confidence=confidence,
            skills_loaded=skills_loaded,
        )

    async def stream_process(self, request: Any) -> AsyncIterator[str]:
        async for chunk in super().stream_process(request):
            yield chunk


# -- Module-level singleton --

_personalisation_service: PersonalisationService | None = None


def get_personalisation_service() -> PersonalisationService:
    """Get or create the Personalisation service singleton."""
    global _personalisation_service
    if _personalisation_service is None:
        _personalisation_service = PersonalisationService()
    return _personalisation_service
