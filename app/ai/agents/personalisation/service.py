# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Personalisation agent service -- injects ESP personalisation syntax into email HTML."""

import contextvars
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
from app.core.logging import get_logger
from app.qa_engine.personalisation_validator import analyze_personalisation
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

_syntax_warnings_var: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "personalisation_syntax_warnings", default=None
)


def format_syntax_warnings(html: str) -> list[str]:
    """Run personalisation syntax validation and return formatted warnings."""
    analysis = analyze_personalisation(html)
    warnings: list[str] = []
    for err in analysis.unbalanced_delimiters:
        warnings.append(f"[error] delimiter_balance: {err}")
    for err in analysis.unbalanced_conditionals:
        warnings.append(f"[error] conditional_balance: {err}")
    for err in analysis.syntax_errors:
        warnings.append(f"[error] syntax: {err}")
    for err in analysis.nested_depth_violations:
        warnings.append(f"[warning] nesting_depth: {err}")
    for err in analysis.empty_fallbacks:
        warnings.append(f"[warning] empty_fallback: {err}")
    if analysis.is_mixed_platform:
        platforms = ", ".join(str(p) for p in analysis.detected_platforms)
        warnings.append(f"[error] mixed_platform: detected {platforms}")
    return warnings


class PersonalisationService(BaseAgentService):
    """Orchestrates the Personalisation agent pipeline.

    Pipeline: detect skills -> build prompt -> LLM call -> validate output ->
    extract HTML -> XSS sanitize -> optional QA checks.
    """

    agent_name = "personalisation"
    model_tier = "standard"
    stream_prefix = "personalise"

    def build_system_prompt(self, relevant_skills: list[str], output_mode: str = "html") -> str:
        return _build_system_prompt(relevant_skills, output_mode=output_mode)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: PersonalisationRequest = request
        return _detect_relevant_skills(req.platform, req.requirements)

    def _post_process(self, raw_content: str) -> str:
        """Post-process LLM output: extract HTML, sanitize, then validate syntax."""
        html = super()._post_process(raw_content)

        warnings = format_syntax_warnings(html)
        _syntax_warnings_var.set(warnings)

        if warnings:
            logger.warning(
                "agents.personalisation.syntax_validation_issues",
                issue_count=len(warnings),
                issues=warnings[:10],
            )

        return html

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
        warnings = _syntax_warnings_var.get(None) or []
        return PersonalisationResponse(
            html=html,
            platform=req.platform,
            tags_injected=skills_loaded,
            syntax_warnings=warnings,
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
