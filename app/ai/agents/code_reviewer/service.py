# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Code Reviewer agent service -- orchestrates LLM -> parse issues -> optional QA."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.code_reviewer.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.code_reviewer.schemas import (
    CodeReviewIssue,
    CodeReviewRequest,
    CodeReviewResponse,
)
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


def _build_user_message(request: CodeReviewRequest) -> str:
    """Build the user message from the request fields."""
    focus_label = "all areas" if request.focus == "all" else request.focus
    return (
        f"Review the following email HTML. Focus on: {focus_label}.\n\nEmail HTML:\n{request.html}"
    )


def _extract_issues(raw_content: str) -> tuple[list[CodeReviewIssue], str]:
    """Extract structured issues from LLM response.

    Looks for a JSON block with 'issues' array and 'summary' field.

    Returns:
        Tuple of (issues list, summary string).
    """
    # Try to find JSON in code fence
    content = raw_content
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        content = content[start:end].strip()

    # Strip confidence comment if present
    content = strip_confidence_comment(content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: return raw content as summary with no structured issues
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


class CodeReviewService:
    """Orchestrates the Code Reviewer agent pipeline.

    Pipeline: detect skills -> build prompt -> LLM call -> validate output ->
    parse issues -> optional QA checks.
    """

    async def process(self, request: CodeReviewRequest) -> CodeReviewResponse:
        """Review email HTML and return structured issues (non-streaming).

        Args:
            request: The Code Review request with HTML and focus area.

        Returns:
            CodeReviewResponse with issues, summary, and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"

        # Progressive disclosure -- load only relevant skill files
        relevant_skills = detect_relevant_skills(request.focus)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.code_reviewer.process_started",
            provider=provider_name,
            model=model,
            focus=request.focus,
            html_length=len(request.html),
            skills_loaded=relevant_skills,
            run_qa=request.run_qa,
        )

        # Resolve provider and call LLM
        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=8192)
        except Exception as e:
            logger.error(
                "agents.code_reviewer.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Code review processing failed") from e

        # Process output: validate -> extract issues
        raw_content = validate_output(result.content)
        confidence = extract_confidence(raw_content)
        issues, summary = _extract_issues(raw_content)

        logger.info(
            "agents.code_reviewer.process_completed",
            model=model_id,
            focus=request.focus,
            issue_count=len(issues),
            confidence=confidence,
            usage=result.usage,
        )

        # Optional QA checks on the input HTML
        qa_results: list[QACheckResult] | None = None
        qa_passed: bool | None = None

        if request.run_qa:
            qa_results = []
            for check in ALL_CHECKS:
                check_result = await check.run(request.html)
                qa_results.append(check_result)
            qa_passed = all(r.passed for r in qa_results)

            logger.info(
                "agents.code_reviewer.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return CodeReviewResponse(
            html=request.html,  # Return original HTML unmodified
            issues=issues,
            summary=summary,
            skills_loaded=relevant_skills,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_process(self, request: CodeReviewRequest) -> AsyncIterator[str]:
        """Stream code review as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete output).

        Args:
            request: The Code Review request with HTML.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"
        response_id = f"review-{uuid.uuid4().hex[:12]}"

        relevant_skills = detect_relevant_skills(request.focus)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.code_reviewer.stream_started",
            provider=provider_name,
            model=model,
            focus=request.focus,
            html_length=len(request.html),
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            async for chunk in provider.stream(messages, model_override=model, max_tokens=8192):  # type: ignore[attr-defined]
                sse_data = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(sse_data)}\n\n"

        except Exception as e:
            logger.error(
                "agents.code_reviewer.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Code review streaming failed") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.code_reviewer.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# -- Module-level singleton --

_code_review_service: CodeReviewService | None = None


def get_code_review_service() -> CodeReviewService:
    """Get or create the Code Review service singleton.

    Returns:
        Singleton CodeReviewService instance.
    """
    global _code_review_service
    if _code_review_service is None:
        _code_review_service = CodeReviewService()
    return _code_review_service
