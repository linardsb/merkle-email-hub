# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Evaluator agent service — adversarial evaluation of another agent's output.

Uses a *different* model provider from the generator to eliminate
self-evaluation bias. Returns structured EvalVerdict with accept/revise/reject.
"""

from __future__ import annotations

import json
from typing import Any, cast

from app.ai.agents.base import BaseAgentService
from app.ai.agents.evaluator.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.evaluator.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.evaluator.schemas import (
    EvalIssue,
    EvaluatorRequest,
    EvaluatorResponse,
    EvalVerdict,
)
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import TaskTier, resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.security.prompt_guard import scan_for_injection
from app.ai.shared import strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


def _extract_json_from_fence(content: str) -> str:
    """Extract JSON content from markdown code fences."""
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        return content[start:end].strip()
    if "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        return content[start:end].strip()
    return content


def _parse_verdict(raw_content: str) -> EvalVerdict:
    """Parse LLM JSON output into an EvalVerdict.

    Handles code-fenced JSON and malformed output gracefully.
    """
    content = strip_confidence_comment(raw_content)
    content = _extract_json_from_fence(content)

    try:
        data: dict[str, Any] = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("evaluator.verdict_parse_failed")
        return EvalVerdict(
            verdict="reject",
            score=0.0,
            feedback="Failed to parse evaluator response",
        )

    issues_raw: list[Any] = data.get("issues", [])
    issues = [
        EvalIssue(
            severity=cast(dict[str, Any], item).get("severity", "minor"),
            category=str(cast(dict[str, Any], item).get("category", "unknown")),
            description=str(cast(dict[str, Any], item).get("description", "")),
            location=cast(dict[str, Any], item).get("location"),
        )
        for item in issues_raw
        if isinstance(item, dict)
    ]

    return EvalVerdict(
        verdict=data.get("verdict", "reject"),
        score=float(data.get("score", 0.0)),
        issues=issues,
        feedback=str(data.get("feedback", "")),
        suggested_corrections=[str(s) for s in data.get("suggested_corrections", [])],
    )


class EvaluatorAgentService(BaseAgentService):
    """Adversarial evaluator — checks another agent's output against brief and criteria."""

    agent_name = "evaluator"
    sanitization_profile = "default"
    model_tier: TaskTier = "complex"
    max_tokens = 2048
    run_qa_default = False
    _output_mode_supported: bool = False

    def _get_model_tier(self, request: Any) -> TaskTier:
        return "complex"

    def _resolve_provider(self) -> str:
        """Select a provider different from the generator to avoid self-eval bias."""
        settings = get_settings()
        eval_provider = settings.ai.evaluator.provider
        if eval_provider:
            return eval_provider
        gen_provider = settings.ai.provider
        return "anthropic" if gen_provider == "openai" else "openai"

    def build_system_prompt(
        self,
        relevant_skills: list[str],
        output_mode: str = "html",
        *,
        client_id: str | None = None,
    ) -> str:
        # Use agent_name from the first skill hint (criteria file), or "generic"
        agent_name = relevant_skills[0] if relevant_skills else "generic"
        return _build_system_prompt(agent_name)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: EvaluatorRequest = request
        return _detect_relevant_skills(req.agent_name)

    def _build_user_message(self, request: Any) -> str:
        req: EvaluatorRequest = request
        parts = [
            f"## Original Brief\n\n{req.original_brief}",
            f"\n\n## Agent Output ({req.agent_name})\n\n{req.agent_output}",
        ]
        if req.quality_criteria:
            criteria_text = "\n".join(f"- {c}" for c in req.quality_criteria)
            parts.append(f"\n\n## Additional Criteria\n\n{criteria_text}")
        if req.previous_feedback:
            parts.append(
                f"\n\n## Previous Feedback (iteration {req.iteration})\n\n{req.previous_feedback}"
            )
        return "".join(parts)

    def _post_process(self, raw_content: str) -> str:
        """Return raw content for JSON parsing — evaluator does not produce HTML."""
        return validate_output(raw_content)

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
    ) -> EvaluatorResponse:
        verdict = _parse_verdict(html)
        return EvaluatorResponse(
            verdict=verdict,
            model=model_id,
            confidence=confidence,
            skills_loaded=skills_loaded,
        )

    async def evaluate(
        self,
        original_brief: str,
        agent_name: str,
        agent_output: str,
        quality_criteria: list[str] | None = None,
        *,
        iteration: int = 0,
        previous_feedback: str | None = None,
    ) -> EvaluatorResponse:
        """Evaluate an agent's output against the original brief.

        Scans for prompt injection in agent_output before evaluation.
        Uses a different provider from the generator when possible.
        """
        scan_result = scan_for_injection(agent_output, mode="warn")
        if not scan_result.clean:
            logger.warning(
                "evaluator.injection_detected",
                flags=scan_result.flags,
                agent=agent_name,
            )

        request = EvaluatorRequest(
            original_brief=original_brief,
            agent_name=agent_name,
            agent_output=agent_output,
            quality_criteria=quality_criteria or [],
            iteration=iteration,
            previous_feedback=previous_feedback,
        )

        # Try to use a different provider for adversarial evaluation
        settings = get_settings()
        eval_provider_name = self._resolve_provider()
        model = resolve_model(self._get_model_tier(request))

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills)

        user_message = self._build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        registry = get_registry()
        try:
            provider = registry.get_llm(eval_provider_name)
        except Exception:
            # Fall back to default provider if eval provider unavailable
            logger.warning(
                "evaluator.provider_fallback",
                requested=eval_provider_name,
                fallback=settings.ai.provider,
            )
            eval_provider_name = settings.ai.provider
            provider = registry.get_llm(eval_provider_name)

        result = await provider.complete(messages, model_override=model, max_tokens=self.max_tokens)

        model_id = f"{eval_provider_name}:{model}"
        raw_content = validate_output(result.content)
        verdict = _parse_verdict(raw_content)

        from app.ai.shared import extract_confidence

        confidence = extract_confidence(raw_content)

        logger.info(
            "evaluator.completed",
            agent=agent_name,
            verdict=verdict.verdict,
            score=verdict.score,
            issue_count=len(verdict.issues),
            model=model_id,
            iteration=iteration,
        )

        return EvaluatorResponse(
            verdict=verdict,
            model=model_id,
            confidence=confidence,
            skills_loaded=relevant_skills,
        )
