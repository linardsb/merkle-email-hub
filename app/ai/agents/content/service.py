# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Content agent service — orchestrates LLM → extract → spam check."""

import json
import re
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.content.prompt import CONTENT_SYSTEM_PROMPT
from app.ai.agents.content.schemas import ContentRequest, ContentResponse, SpamWarning
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks.spam_score import SPAM_TRIGGERS

logger = get_logger(__name__)

# ── Regex patterns for content extraction ──

_CODE_BLOCK_RE = re.compile(
    r"```(?:text|TEXT)?\s*\n(.*?)```",
    re.DOTALL,
)

_ALT_DELIMITER = "---"

# ── Operation-to-tier mapping ──

_OPERATION_TIERS: dict[str, str] = {
    "subject_line": "standard",
    "preheader": "standard",
    "cta": "standard",
    "body_copy": "standard",
    "rewrite": "standard",
    "shorten": "lightweight",
    "expand": "lightweight",
    "tone_adjust": "standard",
}


def extract_content(raw: str) -> list[str]:
    """Extract text alternatives from LLM response.

    Looks for ```text ... ``` code blocks. Falls back to raw content
    if no code block is found. Splits by --- delimiter for multiple
    alternatives.
    """
    match = _CODE_BLOCK_RE.search(raw)
    inner = match.group(1) if match else raw

    parts = inner.split(_ALT_DELIMITER)
    results = [part.strip() for part in parts if part.strip()]
    return results


def check_spam_triggers(texts: list[str]) -> list[SpamWarning]:
    """Scan generated text for known spam trigger words/phrases.

    Returns a list of SpamWarning objects with the trigger and a
    ~40-character context snippet around each match.
    """
    warnings: list[SpamWarning] = []
    for text in texts:
        text_lower = text.lower()
        for trigger in SPAM_TRIGGERS:
            pos = text_lower.find(trigger)
            if pos == -1:
                continue
            # Extract ~40-char context snippet around the trigger
            start = max(0, pos - 15)
            end = min(len(text), pos + len(trigger) + 15)
            context = text[start:end]
            if start > 0:
                context = "..." + context
            if end < len(text):
                context = context + "..."
            warnings.append(SpamWarning(trigger=trigger, context=context))
    return warnings


def _build_user_message(request: ContentRequest) -> str:
    """Build the user message from the request fields."""
    parts: list[str] = [
        f"Operation: {request.operation}",
        f"\nSource text:\n{request.text}",
    ]

    if request.tone:
        parts.append(f"\nTarget tone: {request.tone}")

    if request.brand_voice:
        parts.append(f"\nBrand voice guidelines:\n{request.brand_voice}")

    # Auto-generate 5 subject line alternatives when user doesn't specify
    effective_alternatives = request.num_alternatives
    if request.operation == "subject_line" and request.num_alternatives == 1:
        effective_alternatives = 5

    if effective_alternatives > 1:
        parts.append(
            f"\nGenerate {effective_alternatives} distinct alternatives, "
            "separated by --- on its own line."
        )

    return "\n".join(parts)


class ContentService:
    """Orchestrates the content agent pipeline.

    Pipeline: build messages → LLM call → validate output →
    extract content → spam check.
    """

    async def generate(self, request: ContentRequest) -> ContentResponse:
        """Generate content via LLM with spam detection."""
        settings = get_settings()
        provider_name = settings.ai.provider
        tier = _OPERATION_TIERS.get(request.operation, "standard")
        model = resolve_model(tier)  # type: ignore[arg-type]
        model_id = f"{provider_name}:{model}"

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=CONTENT_SYSTEM_PROMPT),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.content.generate_started",
            operation=request.operation,
            provider=provider_name,
            model=model,
            text_length=len(request.text),
            num_alternatives=request.num_alternatives,
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=2048)
        except Exception as e:
            logger.error(
                "agents.content.generate_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError(f"Content generation failed: {e}") from e

        raw_content = validate_output(result.content)
        alternatives = extract_content(raw_content)
        warnings = check_spam_triggers(alternatives)

        logger.info(
            "agents.content.generate_completed",
            model=model_id,
            operation=request.operation,
            alternatives_count=len(alternatives),
            spam_warnings_count=len(warnings),
            usage=result.usage,
        )

        return ContentResponse(
            content=alternatives,
            operation=request.operation,
            spam_warnings=warnings,
            model=model_id,
        )

    async def stream_generate(self, request: ContentRequest) -> AsyncIterator[str]:
        """Stream content generation via SSE."""
        settings = get_settings()
        provider_name = settings.ai.provider
        tier = _OPERATION_TIERS.get(request.operation, "standard")
        model = resolve_model(tier)  # type: ignore[arg-type]
        model_id = f"{provider_name}:{model}"
        response_id = f"content-{uuid.uuid4().hex[:12]}"

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=CONTENT_SYSTEM_PROMPT),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.content.stream_started",
            operation=request.operation,
            provider=provider_name,
            model=model,
            text_length=len(request.text),
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            async for chunk in provider.stream(messages, model_override=model, max_tokens=2048):  # type: ignore[attr-defined]
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
                "agents.content.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError(f"Content streaming failed: {e}") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.content.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# ── Module-level singleton ──

_content_service: ContentService | None = None


def get_content_service() -> ContentService:
    """Get or create the content service singleton."""
    global _content_service
    if _content_service is None:
        _content_service = ContentService()
    return _content_service
