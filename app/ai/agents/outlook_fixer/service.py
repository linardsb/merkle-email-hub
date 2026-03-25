# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401, ARG002
"""Outlook Fixer agent service — fixes Outlook rendering issues in email HTML."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai.multimodal import ContentBlock

from app.ai.agents.base import CONFIDENCE_INSTRUCTION, BaseAgentService
from app.ai.agents.html_summarizer import prepare_html_context
from app.ai.agents.outlook_fixer.mso_repair import (
    format_validation_errors,
    repair_mso_issues,
)
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
from app.ai.agents.schemas.outlook_diagnostic import MSOIssue, OutlookDiagnostic
from app.ai.agents.validation_loop import CRAGMixin
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import TaskTier, resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.mso_parser import MSOValidationResult, validate_mso_conditionals
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


class OutlookFixerService(CRAGMixin, BaseAgentService):
    """Orchestrates the Outlook Fixer agent pipeline.

    Pipeline: detect skills → build prompt → LLM call → validate output →
    extract HTML → XSS sanitize → MSO validate → programmatic repair →
    optional LLM retry → optional QA checks.
    """

    agent_name = "outlook_fixer"
    sanitization_profile = "outlook_fixer"
    model_tier: TaskTier = "standard"
    stream_prefix = "outlook-fix"
    _output_mode_supported: bool = True

    def build_system_prompt(self, relevant_skills: list[str], output_mode: str = "html") -> str:
        return _build_system_prompt(relevant_skills, output_mode=output_mode)

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

    async def _process_structured(self, request: Any) -> OutlookFixerResponse:
        """Structured mode: diagnostic-only, reports MSO issues without fixing HTML."""
        from app.ai.protocols import Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.ai.sanitize import sanitize_prompt
        from app.core.config import get_settings

        req: OutlookFixerRequest = request
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self.model_tier)
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills, output_mode="structured")

        plan_data = req.build_plan or {}
        user_message = (
            "Analyze the following EmailBuildPlan for MSO/Outlook compatibility issues. "
            "Report issues but do NOT fix them — golden templates handle MSO compatibility.\n\n"
            f"Plan: {json.dumps(plan_data, default=str)}\n\n"
            "Return a JSON object with:\n"
            "- issues: array of {issue_type, severity (critical/warning/info), location, recommendation}\n"
            "- template_bug: boolean (true if golden template has MSO issues)\n"
            "- composition_bug: boolean (true if TemplateComposer introduced issues)\n"
            "- overall_mso_safe: boolean\n"
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

        diagnostic = self._parse_diagnostic(result.content)

        logger.info(
            "agents.outlook_fixer.diagnostic_completed",
            issues=len(diagnostic.issues),
            mso_safe=diagnostic.overall_mso_safe,
            confidence=diagnostic.confidence,
        )

        return OutlookFixerResponse(
            html=req.html or "",
            model=model_id,
            confidence=diagnostic.confidence,
            skills_loaded=relevant_skills,
            diagnostic=diagnostic,
        )

    def _parse_diagnostic(self, raw_content: str) -> OutlookDiagnostic:
        """Parse LLM response into OutlookDiagnostic."""
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
            logger.warning("agents.outlook_fixer.diagnostic_parse_failed")
            return OutlookDiagnostic(confidence=0.0, reasoning="Failed to parse")

        issues = tuple(
            MSOIssue(
                issue_type=str(i.get("issue_type", "")),
                severity=i.get("severity", "info"),
                location=str(i.get("location", "")),
                recommendation=str(i.get("recommendation", "")),
            )
            for i in data.get("issues", [])
            if isinstance(i, dict)
        )

        return OutlookDiagnostic(
            issues=issues,
            template_bug=bool(data.get("template_bug", False)),
            composition_bug=bool(data.get("composition_bug", False)),
            overall_mso_safe=bool(data.get("overall_mso_safe", True)),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )

    async def process(self, request: Any, context_blocks: list[ContentBlock] | None = None) -> Any:
        """Execute pipeline with post-generation MSO validation and repair.

        Flow: LLM call → MSO validate → programmatic repair → (optional) LLM retry → QA.
        Max 1 retry to avoid loops.
        """
        response: OutlookFixerResponse = await super().process(request, context_blocks)

        # Validate MSO structure
        mso_result = validate_mso_conditionals(response.html)

        if mso_result.is_valid:
            response.mso_validation_warnings = []
            return response

        # Attempt programmatic repair
        repaired_html, repairs = repair_mso_issues(response.html, mso_result)

        # Re-validate after repair
        post_repair_result = validate_mso_conditionals(repaired_html)

        if post_repair_result.is_valid:
            logger.info(
                "agents.outlook_fixer.mso_repaired_programmatically",
                repairs=repairs,
            )
            response.html = repaired_html
            response.mso_validation_warnings = repairs
            return response

        # Programmatic repair insufficient — retry LLM with error context
        logger.warning(
            "agents.outlook_fixer.mso_repair_insufficient",
            remaining_issues=len(post_repair_result.issues),
            attempting_retry=True,
        )

        retry_response = await self._retry_with_mso_errors(
            request, repaired_html, post_repair_result
        )

        if retry_response is not None:
            return retry_response

        # Retry failed or didn't improve — return repaired version with warnings
        response.html = repaired_html
        response.mso_validation_warnings = [
            f"MSO: {issue.message}" for issue in post_repair_result.issues
        ]
        return response

    async def _retry_with_mso_errors(
        self,
        request: Any,
        current_html: str,
        mso_result: MSOValidationResult,
    ) -> OutlookFixerResponse | None:
        """Retry LLM call with structured MSO error context.

        Returns improved response if retry succeeds, None if it doesn't improve.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self._get_model_tier(request))
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills)
        system_prompt += CONFIDENCE_INSTRUCTION

        error_context = format_validation_errors(mso_result)
        retry_message = (
            f"Your previous output has MSO validation errors. Fix them in this HTML:\n\n"
            f"{prepare_html_context(current_html)}\n\n{error_context}"
        )

        # Retry path — mark system prompt for caching
        messages = [
            Message(role="system", content=system_prompt, cache_control={"type": "ephemeral"}),
            Message(role="user", content=sanitize_prompt(retry_message)),
        ]

        try:
            registry = get_registry()
            provider = registry.get_llm(provider_name)
            result = await provider.complete(
                messages, model_override=model, max_tokens=self.max_tokens
            )
        except Exception as e:
            logger.error(
                "agents.outlook_fixer.mso_retry_failed",
                error=str(e),
            )
            return None

        raw_content = validate_output(result.content)
        confidence = extract_confidence(raw_content)
        retry_html = self._post_process(raw_content)

        # Validate retry result
        retry_mso = validate_mso_conditionals(retry_html)

        if len(retry_mso.issues) >= len(mso_result.issues):
            logger.warning("agents.outlook_fixer.mso_retry_no_improvement")
            return None

        logger.info(
            "agents.outlook_fixer.mso_retry_improved",
            issues_before=len(mso_result.issues),
            issues_after=len(retry_mso.issues),
        )

        # Build response from retry
        should_run_qa = self._should_run_qa(request)
        qa_results: list[QACheckResult] | None = None
        qa_passed: bool | None = None

        if should_run_qa:
            qa_results_list, qa_passed = await self._run_qa(retry_html)
            qa_results = qa_results_list

        return OutlookFixerResponse(
            html=sanitize_html_xss(retry_html, profile=self.sanitization_profile),
            fixes_applied=relevant_skills,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
            confidence=confidence,
            skills_loaded=relevant_skills,
            mso_validation_warnings=[f"MSO: {issue.message}" for issue in retry_mso.issues]
            if not retry_mso.is_valid
            else ["MSO: All issues resolved after retry"],
        )

    async def stream_process(
        self, request: Any, context_blocks: list[ContentBlock] | None = None
    ) -> AsyncIterator[str]:
        async for chunk in super().stream_process(request, context_blocks):
            yield chunk


# ── Module-level singleton ──

_outlook_fixer_service: OutlookFixerService | None = None


def get_outlook_fixer_service() -> OutlookFixerService:
    """Get or create the Outlook Fixer service singleton."""
    global _outlook_fixer_service
    if _outlook_fixer_service is None:
        _outlook_fixer_service = OutlookFixerService()
    return _outlook_fixer_service
