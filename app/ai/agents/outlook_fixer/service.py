# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Outlook Fixer agent service — orchestrates LLM → extract → sanitize → QA."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.outlook_fixer.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.outlook_fixer.schemas import (
    OutlookFixerRequest,
    OutlookFixerResponse,
)
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_html, sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


def _build_user_message(request: OutlookFixerRequest) -> str:
    """Build the user message from the request fields.

    Combines the HTML with optional issue hints.

    Args:
        request: The Outlook Fixer request.

    Returns:
        Formatted user message string.
    """
    parts: list[str] = [
        "Fix the following email HTML for Outlook desktop compatibility:\n",
        request.html,
    ]

    if request.issues:
        issues_str = ", ".join(request.issues)
        parts.append(f"\n\nSpecific issues to address: {issues_str}")

    return "\n".join(parts)


class OutlookFixerService:
    """Orchestrates the Outlook Fixer agent pipeline.

    Pipeline: detect skills → build prompt → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    async def process(self, request: OutlookFixerRequest) -> OutlookFixerResponse:
        """Fix Outlook rendering issues in email HTML (non-streaming).

        Args:
            request: The Outlook Fixer request with HTML and options.

        Returns:
            OutlookFixerResponse with fixed HTML and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"

        # Progressive disclosure — load only relevant skill files
        relevant_skills = detect_relevant_skills(request.html, request.issues)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.outlook_fixer.process_started",
            provider=provider_name,
            model=model,
            html_length=len(request.html),
            skills_loaded=relevant_skills,
            has_explicit_issues=request.issues is not None,
            run_qa=request.run_qa,
        )

        # Resolve provider and call LLM
        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=8192)
        except Exception as e:
            logger.error(
                "agents.outlook_fixer.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Outlook Fixer processing failed") from e

        # Process output: validate → extract → XSS sanitize
        raw_content = validate_output(result.content)
        html = extract_html(raw_content)
        html = sanitize_html_xss(html)

        logger.info(
            "agents.outlook_fixer.process_completed",
            model=model_id,
            html_length=len(html),
            usage=result.usage,
        )

        # Optional QA checks
        qa_results: list[QACheckResult] | None = None
        qa_passed: bool | None = None

        if request.run_qa:
            qa_results = []
            for check in ALL_CHECKS:
                check_result = await check.run(html)
                qa_results.append(check_result)
            qa_passed = all(r.passed for r in qa_results)

            logger.info(
                "agents.outlook_fixer.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return OutlookFixerResponse(
            html=html,
            fixes_applied=relevant_skills,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_process(self, request: OutlookFixerRequest) -> AsyncIterator[str]:
        """Stream Outlook fix as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete HTML).

        Args:
            request: The Outlook Fixer request with HTML.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"
        response_id = f"outlook-fix-{uuid.uuid4().hex[:12]}"

        relevant_skills = detect_relevant_skills(request.html, request.issues)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.outlook_fixer.stream_started",
            provider=provider_name,
            model=model,
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
                "agents.outlook_fixer.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Outlook Fixer streaming failed") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.outlook_fixer.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# ── Module-level singleton ──

_outlook_fixer_service: OutlookFixerService | None = None


def get_outlook_fixer_service() -> OutlookFixerService:
    """Get or create the Outlook Fixer service singleton.

    Returns:
        Singleton OutlookFixerService instance.
    """
    global _outlook_fixer_service
    if _outlook_fixer_service is None:
        _outlook_fixer_service = OutlookFixerService()
    return _outlook_fixer_service
