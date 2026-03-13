# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401, ARG002
"""Code Reviewer agent service -- orchestrates LLM -> parse issues -> optional QA."""

import contextvars
import json
from collections.abc import AsyncIterator
from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.agents.code_reviewer.actionability import (
    enrich_with_qa_results,
    format_non_actionable_for_retry,
    is_actionable,
    validate_and_enrich_issues,
)
from app.ai.agents.code_reviewer.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.code_reviewer.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.code_reviewer.schemas import (
    CodeReviewIssue,
    CodeReviewRequest,
    CodeReviewResponse,
)
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

_actionability_warnings_var: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "code_reviewer_actionability_warnings", default=None
)


def get_actionability_warnings() -> list[str]:
    """Get actionability warnings from the current request context."""
    return _actionability_warnings_var.get() or []


def _extract_json_from_fence(content: str) -> str:
    """Extract JSON content from markdown code fences.

    Handles ```json and plain ``` fences.
    """
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        return content[start:end].strip()
    if "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        return content[start:end].strip()
    return content


def _extract_issues(raw_content: str) -> tuple[list[CodeReviewIssue], str]:
    """Extract structured issues from LLM response.

    Looks for a JSON block with 'issues' array and 'summary' field.
    """
    content = _extract_json_from_fence(raw_content)
    content = strip_confidence_comment(content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [], raw_content.strip()

    issues: list[CodeReviewIssue] = []
    raw_issues = data.get("issues", [])
    for item in raw_issues:
        if isinstance(item, dict):
            issues.append(
                CodeReviewIssue(
                    rule=str(item.get("rule", "unknown")),
                    severity=item.get("severity", "info"),
                    line_hint=item.get("line_hint"),
                    message=str(item.get("message", "")),
                    suggestion=item.get("suggestion"),
                    current_value=item.get("current_value"),
                    fix_value=item.get("fix_value"),
                    affected_clients=item.get("affected_clients"),
                )
            )

    summary = str(data.get("summary", f"Found {len(issues)} issue(s)."))
    return issues, summary


class CodeReviewService(BaseAgentService):
    """Orchestrates the Code Reviewer agent pipeline.

    Pipeline: detect skills -> build prompt -> LLM call -> validate output ->
    parse issues -> actionability validation -> selective retry ->
    agent tagging -> optional QA cross-check.
    """

    agent_name = "code_reviewer"
    model_tier = "standard"
    stream_prefix = "review"

    def build_system_prompt(self, relevant_skills: list[str]) -> str:
        return _build_system_prompt(relevant_skills)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: CodeReviewRequest = request
        return _detect_relevant_skills(req.focus)

    def _build_user_message(self, request: Any) -> str:
        req: CodeReviewRequest = request
        focus_label = "all areas" if req.focus == "all" else req.focus
        return (
            f"Review the following email HTML. Focus on: {focus_label}.\n\nEmail HTML:\n{req.html}"
        )

    def _post_process(self, raw_content: str) -> str:
        """Code reviewer returns raw content for JSON extraction, not HTML."""
        return validate_output(raw_content)

    async def _run_qa(self, html: str) -> tuple[list[QACheckResult], bool]:
        """Run QA on the original input HTML."""
        qa_results: list[QACheckResult] = []
        for check in ALL_CHECKS:
            check_result = await check.run(html)
            qa_results.append(check_result)
        qa_passed = all(r.passed for r in qa_results)
        return qa_results, qa_passed

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
    ) -> CodeReviewResponse:
        req: CodeReviewRequest = request
        # For code reviewer, "html" is actually raw LLM output (via overridden _post_process)
        issues, summary = _extract_issues(html)
        return CodeReviewResponse(
            html=req.html,  # Return original HTML unmodified
            issues=issues,
            summary=summary,
            skills_loaded=skills_loaded,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
            confidence=confidence,
        )

    def _should_run_qa(self, request: Any) -> bool:
        """Code reviewer suppresses QA in base pipeline — runs it on input HTML instead."""
        return False

    async def process(self, request: Any) -> CodeReviewResponse:
        """Execute pipeline with post-generation actionability validation.

        Flow: LLM call -> extract issues -> validate actionability ->
        (optional) selective retry for non-actionable -> agent tagging ->
        (optional) QA cross-check -> response.
        """
        response: CodeReviewResponse = await super().process(request)

        # Step 1: Validate and enrich issues (agent tagging + actionability check)
        enriched_issues, act_warnings = validate_and_enrich_issues(response.issues)

        # Step 2: Selective retry for non-actionable issues (max 1 retry)
        non_actionable = [i for i in enriched_issues if not is_actionable(i)]
        if non_actionable:
            retry_prompt = format_non_actionable_for_retry(enriched_issues)
            if retry_prompt:
                improved = await self._retry_non_actionable(retry_prompt)
                if improved:
                    enriched_issues = self._merge_retry_results(enriched_issues, improved)
                    # Re-validate after merge
                    enriched_issues, act_warnings = validate_and_enrich_issues(enriched_issues)

        _actionability_warnings_var.set(act_warnings)

        # Step 3: Run QA on input HTML if requested (or if enrichment needs it)
        req: CodeReviewRequest = request
        needs_qa = bool(getattr(request, "run_qa", False)) or req.enrich_with_qa
        qa_results_list: list[QACheckResult] | None = None
        qa_passed: bool | None = None

        if needs_qa:
            qa_results_list, qa_passed = await self._run_qa(req.html)

        # Step 4: Optional QA cross-check enrichment
        if req.enrich_with_qa and qa_results_list:
            _, qa_warnings = enrich_with_qa_results(enriched_issues, qa_results_list)
            act_warnings.extend(qa_warnings)

        return CodeReviewResponse(
            html=req.html,
            issues=enriched_issues,
            summary=response.summary,
            skills_loaded=response.skills_loaded,
            qa_results=qa_results_list,
            qa_passed=qa_passed,
            model=response.model,
            confidence=response.confidence,
            actionability_warnings=act_warnings,
        )

    async def _retry_non_actionable(
        self,
        retry_prompt: str,
    ) -> list[CodeReviewIssue] | None:
        """Retry LLM with only the non-actionable issues for reformatting.

        Sends the retry prompt (no HTML -- just the vague issues) and parses
        the improved suggestions. Returns None if retry fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self.model_tier)

        messages = [
            Message(
                role="system",
                content=(
                    "You are an email HTML code review assistant. Rewrite vague "
                    "suggestions into concrete 'change X to Y' format with "
                    "current_value, fix_value, and affected_clients."
                ),
            ),
            Message(role="user", content=sanitize_prompt(retry_prompt)),
        ]

        try:
            registry = get_registry()
            provider = registry.get_llm(provider_name)
            result = await provider.complete(messages, model_override=model, max_tokens=2048)
        except Exception as e:
            logger.warning(
                "agents.code_reviewer.actionability_retry_failed",
                error=str(e),
            )
            return None

        raw = validate_output(result.content)
        clean = strip_confidence_comment(raw)
        content = _extract_json_from_fence(clean)

        try:
            data = json.loads(content)
            if not isinstance(data, list):
                return None
        except json.JSONDecodeError:
            return None

        improved: list[CodeReviewIssue] = []
        for item in data:
            if isinstance(item, dict):
                improved.append(
                    CodeReviewIssue(
                        rule=str(item.get("rule", "unknown")),
                        severity=item.get("severity", "info"),
                        line_hint=item.get("line_hint"),
                        message=str(item.get("message", "")),
                        suggestion=item.get("suggestion"),
                        current_value=item.get("current_value"),
                        fix_value=item.get("fix_value"),
                        affected_clients=item.get("affected_clients"),
                    )
                )

        if improved:
            logger.info(
                "agents.code_reviewer.actionability_retry_improved",
                improved_count=len(improved),
            )

        return improved if improved else None

    def _merge_retry_results(
        self,
        original: list[CodeReviewIssue],
        improved: list[CodeReviewIssue],
    ) -> list[CodeReviewIssue]:
        """Merge retry-improved issues back into the original list.

        Matches by rule ID. If an improved version exists, replace the original.
        """
        improved_by_rule = {i.rule: i for i in improved}
        merged: list[CodeReviewIssue] = []
        for issue in original:
            if issue.rule in improved_by_rule and is_actionable(improved_by_rule[issue.rule]):
                merged.append(improved_by_rule[issue.rule])
            else:
                merged.append(issue)
        return merged

    async def stream_process(self, request: Any) -> AsyncIterator[str]:
        async for chunk in super().stream_process(request):
            yield chunk


# -- Module-level singleton --

_code_review_service: CodeReviewService | None = None


def get_code_review_service() -> CodeReviewService:
    """Get or create the Code Review service singleton."""
    global _code_review_service
    if _code_review_service is None:
        _code_review_service = CodeReviewService()
    return _code_review_service
