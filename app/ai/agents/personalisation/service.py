# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401, ARG002
"""Personalisation agent service -- injects ESP personalisation syntax into email HTML."""

import contextvars
import json
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
from app.ai.agents.schemas.personalisation_decisions import (
    PersonalisationDecisions,
    VariablePlacement,
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
    _output_mode_supported: bool = True

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

    async def _process_structured(self, request: Any) -> PersonalisationResponse:
        """Structured mode: analyze plan and return personalisation decisions."""
        from app.ai.protocols import Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.ai.sanitize import sanitize_prompt
        from app.core.config import get_settings

        req: PersonalisationRequest = request
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self.model_tier)
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills, output_mode="structured")

        plan_data = req.build_plan or {}
        user_message = (
            f"Analyze the following EmailBuildPlan for {req.platform} personalisation.\n\n"
            f"Plan: {json.dumps(plan_data, default=str)}\n\n"
            f"Requirements: {req.requirements}\n\n"
            "Return a JSON object with:\n"
            "- esp_platform: string\n"
            "- variables: array of {slot_id, variable_name, fallback_value, syntax}\n"
            "- conditional_blocks: array of slot_ids needing conditionals\n"
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

        decisions = self._parse_personalisation_decisions(result.content)

        logger.info(
            "agents.personalisation.structured_completed",
            variables=len(decisions.variables),
            platform=decisions.esp_platform,
            confidence=decisions.confidence,
        )

        return PersonalisationResponse(
            html="",
            platform=req.platform,
            tags_injected=[],
            syntax_warnings=[],
            model=model_id,
            confidence=decisions.confidence,
            skills_loaded=relevant_skills,
            decisions=decisions,
        )

    def _parse_personalisation_decisions(self, raw_content: str) -> PersonalisationDecisions:
        """Parse LLM response into PersonalisationDecisions."""
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
            logger.warning("agents.personalisation.structured_parse_failed")
            return PersonalisationDecisions(
                confidence=0.0, reasoning="Failed to parse LLM response"
            )

        variables = tuple(
            VariablePlacement(
                slot_id=str(v.get("slot_id", "")),
                variable_name=str(v.get("variable_name", "")),
                fallback_value=str(v.get("fallback_value", "")),
                syntax=str(v.get("syntax", "")),
            )
            for v in data.get("variables", [])
            if isinstance(v, dict)
        )

        conditional_blocks = tuple(str(c) for c in data.get("conditional_blocks", []))

        return PersonalisationDecisions(
            esp_platform=str(data.get("esp_platform", "")),
            variables=variables,
            conditional_blocks=conditional_blocks,
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
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
