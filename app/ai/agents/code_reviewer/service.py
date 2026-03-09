# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401, ARG002
"""Code Reviewer agent service -- orchestrates LLM -> parse issues -> optional QA."""

import json
from collections.abc import AsyncIterator
from typing import Any

from app.ai.agents.base import BaseAgentService
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
from app.ai.sanitize import validate_output
from app.ai.shared import strip_confidence_comment
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import QACheckResult


def _extract_issues(raw_content: str) -> tuple[list[CodeReviewIssue], str]:
    """Extract structured issues from LLM response.

    Looks for a JSON block with 'issues' array and 'summary' field.
    """
    content = raw_content
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        content = content[start:end].strip()

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
                )
            )

    summary = str(data.get("summary", f"Found {len(issues)} issue(s)."))
    return issues, summary


class CodeReviewService(BaseAgentService):
    """Orchestrates the Code Reviewer agent pipeline.

    Pipeline: detect skills -> build prompt -> LLM call -> validate output ->
    parse issues -> optional QA checks.
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
        """Code reviewer runs QA on the original input HTML, not the output.

        But _run_qa receives the post-processed output. We override process()
        to handle this correctly.
        """
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
        """Override to run QA on the INPUT html instead of the output."""
        response: CodeReviewResponse = await super().process(request)

        # Run QA on the original input HTML (not the LLM output)
        original_run_qa = bool(getattr(request, "run_qa", self.run_qa_default))
        if original_run_qa:
            req: CodeReviewRequest = request
            qa_results_list, qa_passed = await self._run_qa(req.html)
            response = CodeReviewResponse(
                html=response.html,
                issues=response.issues,
                summary=response.summary,
                skills_loaded=response.skills_loaded,
                qa_results=qa_results_list,
                qa_passed=qa_passed,
                model=response.model,
                confidence=response.confidence,
            )

        return response

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
