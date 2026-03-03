# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Dark Mode agent service — orchestrates LLM → extract → sanitize → QA."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.dark_mode.prompt import DARK_MODE_SYSTEM_PROMPT
from app.ai.agents.dark_mode.schemas import DarkModeRequest, DarkModeResponse
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_html, sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.checks.dark_mode import DarkModeCheck
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


def _build_user_message(request: DarkModeRequest) -> str:
    """Build the user message from the request fields.

    Combines the HTML with optional colour override and preserve instructions.

    Args:
        request: The dark mode request.

    Returns:
        Formatted user message string.
    """
    parts: list[str] = [
        "Enhance the following email HTML with comprehensive dark mode support:\n",
        request.html,
    ]

    if request.color_overrides:
        overrides = ", ".join(f"{k} → {v}" for k, v in request.color_overrides.items())
        parts.append(f"\n\nUse these specific colour mappings: {overrides}")

    if request.preserve_colors:
        preserved = ", ".join(request.preserve_colors)
        parts.append(f"\n\nDo NOT remap these colours (keep them unchanged): {preserved}")

    return "\n".join(parts)


class DarkModeService:
    """Orchestrates the dark mode agent pipeline.

    Pipeline: build messages → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    async def process(self, request: DarkModeRequest) -> DarkModeResponse:
        """Enhance email HTML with dark mode support (non-streaming).

        Args:
            request: The dark mode request with HTML and options.

        Returns:
            DarkModeResponse with enhanced HTML and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"

        # Build messages with system prompt and sanitized user message
        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=DARK_MODE_SYSTEM_PROMPT),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.dark_mode.process_started",
            provider=provider_name,
            model=model,
            html_length=len(request.html),
            has_color_overrides=request.color_overrides is not None,
            has_preserve_colors=request.preserve_colors is not None,
            run_qa=request.run_qa,
        )

        # Resolve provider and call LLM
        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=8192)
        except Exception as e:
            logger.error(
                "agents.dark_mode.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError(f"Dark mode processing failed: {e}") from e

        # Process output: validate → extract → XSS sanitize
        raw_content = validate_output(result.content)
        html = extract_html(raw_content)
        html = sanitize_html_xss(html)

        logger.info(
            "agents.dark_mode.process_completed",
            model=model_id,
            html_length=len(html),
            usage=result.usage,
        )

        # Optional QA checks — run dark mode check first for primary signal
        qa_results: list[QACheckResult] | None = None
        qa_passed: bool | None = None

        if request.run_qa:
            qa_results = []

            # Dark mode check first (primary signal)
            dm_check = DarkModeCheck()
            dm_result = await dm_check.run(html)
            qa_results.append(dm_result)

            # Remaining checks (skip duplicate dark mode check)
            for check in ALL_CHECKS:
                if isinstance(check, DarkModeCheck):
                    continue
                check_result = await check.run(html)
                qa_results.append(check_result)

            qa_passed = all(r.passed for r in qa_results)

            logger.info(
                "agents.dark_mode.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return DarkModeResponse(
            html=html,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_process(self, request: DarkModeRequest) -> AsyncIterator[str]:
        """Stream dark mode enhancement as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete HTML).

        Args:
            request: The dark mode request with HTML.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"
        response_id = f"darkmode-{uuid.uuid4().hex[:12]}"

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=DARK_MODE_SYSTEM_PROMPT),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.dark_mode.stream_started",
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
                "agents.dark_mode.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError(f"Dark mode streaming failed: {e}") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.dark_mode.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# ── Module-level singleton ──

_dark_mode_service: DarkModeService | None = None


def get_dark_mode_service() -> DarkModeService:
    """Get or create the dark mode service singleton.

    Returns:
        Singleton DarkModeService instance.
    """
    global _dark_mode_service
    if _dark_mode_service is None:
        _dark_mode_service = DarkModeService()
    return _dark_mode_service
