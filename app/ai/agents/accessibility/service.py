# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Accessibility Auditor agent service — orchestrates LLM → extract → sanitize → QA."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.accessibility.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.accessibility.schemas import (
    AccessibilityRequest,
    AccessibilityResponse,
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


def _build_user_message(request: AccessibilityRequest) -> str:
    """Build the user message from the request fields."""
    parts: list[str] = [
        "Audit and fix the following email HTML for WCAG 2.1 AA accessibility:\n",
        request.html,
    ]

    if request.focus_areas:
        areas_str = ", ".join(request.focus_areas)
        parts.append(f"\n\nFocus on these areas: {areas_str}")

    return "\n".join(parts)


class AccessibilityService:
    """Orchestrates the Accessibility Auditor agent pipeline.

    Pipeline: detect skills → build prompt → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    async def process(self, request: AccessibilityRequest) -> AccessibilityResponse:
        """Audit and fix accessibility issues in email HTML (non-streaming).

        Args:
            request: The accessibility audit request with HTML and options.

        Returns:
            AccessibilityResponse with fixed HTML and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"

        # Progressive disclosure — load only relevant skill files
        relevant_skills = detect_relevant_skills(request.html, request.focus_areas)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.accessibility.process_started",
            provider=provider_name,
            model=model,
            html_length=len(request.html),
            skills_loaded=relevant_skills,
            has_focus_areas=request.focus_areas is not None,
            run_qa=request.run_qa,
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=8192)
        except Exception as e:
            logger.error(
                "agents.accessibility.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Accessibility audit processing failed") from e

        # Process output: validate → extract → XSS sanitize
        raw_content = validate_output(result.content)
        html = extract_html(raw_content)
        html = sanitize_html_xss(html)

        logger.info(
            "agents.accessibility.process_completed",
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
                "agents.accessibility.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return AccessibilityResponse(
            html=html,
            skills_loaded=relevant_skills,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_process(self, request: AccessibilityRequest) -> AsyncIterator[str]:
        """Stream accessibility fix as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete HTML).

        Args:
            request: The accessibility audit request with HTML.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"
        response_id = f"a11y-fix-{uuid.uuid4().hex[:12]}"

        relevant_skills = detect_relevant_skills(request.html, request.focus_areas)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.accessibility.stream_started",
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
                "agents.accessibility.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Accessibility audit streaming failed") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.accessibility.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# ── Module-level singleton ──

_accessibility_service: AccessibilityService | None = None


def get_accessibility_service() -> AccessibilityService:
    """Get or create the Accessibility service singleton.

    Returns:
        Singleton AccessibilityService instance.
    """
    global _accessibility_service
    if _accessibility_service is None:
        _accessibility_service = AccessibilityService()
    return _accessibility_service
