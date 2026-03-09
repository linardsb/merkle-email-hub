# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Personalisation agent service -- orchestrates LLM -> extract -> sanitize -> QA."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.personalisation.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.personalisation.schemas import (
    PersonalisationRequest,
    PersonalisationResponse,
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


def _build_user_message(request: PersonalisationRequest) -> str:
    """Build the user message from the request fields."""
    return (
        f"Add personalisation to the following email HTML for the {request.platform} platform.\n\n"
        f"Requirements:\n{request.requirements}\n\n"
        f"Email HTML:\n{request.html}"
    )


class PersonalisationService:
    """Orchestrates the Personalisation agent pipeline.

    Pipeline: detect skills -> build prompt -> LLM call -> validate output ->
    extract HTML -> XSS sanitize -> optional QA checks.
    """

    async def process(self, request: PersonalisationRequest) -> PersonalisationResponse:
        """Inject ESP personalisation syntax into email HTML (non-streaming).

        Args:
            request: The Personalisation request with HTML, platform, and requirements.

        Returns:
            PersonalisationResponse with personalised HTML and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"

        # Progressive disclosure -- load only relevant skill files
        relevant_skills = detect_relevant_skills(request.platform, request.requirements)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.personalisation.process_started",
            provider=provider_name,
            model=model,
            platform=request.platform,
            html_length=len(request.html),
            requirements_length=len(request.requirements),
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
                "agents.personalisation.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Personalisation processing failed") from e

        # Process output: validate -> extract -> XSS sanitize
        raw_content = validate_output(result.content)
        html = extract_html(raw_content)
        html = sanitize_html_xss(html)

        logger.info(
            "agents.personalisation.process_completed",
            model=model_id,
            platform=request.platform,
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
                "agents.personalisation.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return PersonalisationResponse(
            html=html,
            platform=request.platform,
            tags_injected=relevant_skills,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_process(self, request: PersonalisationRequest) -> AsyncIterator[str]:
        """Stream personalisation as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete HTML).

        Args:
            request: The Personalisation request with HTML.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"
        response_id = f"personalise-{uuid.uuid4().hex[:12]}"

        relevant_skills = detect_relevant_skills(request.platform, request.requirements)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.personalisation.stream_started",
            provider=provider_name,
            model=model,
            platform=request.platform,
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
                "agents.personalisation.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Personalisation streaming failed") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.personalisation.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# -- Module-level singleton --

_personalisation_service: PersonalisationService | None = None


def get_personalisation_service() -> PersonalisationService:
    """Get or create the Personalisation service singleton.

    Returns:
        Singleton PersonalisationService instance.
    """
    global _personalisation_service
    if _personalisation_service is None:
        _personalisation_service = PersonalisationService()
    return _personalisation_service
