# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Chat orchestration service using the LLMProvider protocol.

Provider-agnostic: resolves the configured provider from the registry
and delegates completion to it. Includes model routing, PII sanitization,
and output validation.
"""

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.exceptions import AIExecutionError
from app.ai.fallback import call_with_fallback
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import get_fallback_chain, resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    UsageInfo,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Orchestrates chat interactions using a protocol-based LLM provider.

    Features:
    - Provider resolution from registry
    - Model tier routing (complex/standard/lightweight)
    - PII sanitization before external API calls
    - Output validation on responses
    - Streaming support via async iterator
    """

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Process a non-streaming chat completion request.

        Args:
            request: The chat completion request with messages.

        Returns:
            ChatCompletionResponse with the provider's response.

        Raises:
            AIExecutionError: If the provider fails to generate a response.
        """
        settings = get_settings()
        provider_name = settings.ai.provider

        # Resolve model via tier routing
        model = resolve_model(request.task_tier)
        model_id = f"{provider_name}:{model}"

        # Sanitize messages (strip PII before sending to external API)
        messages = [
            Message(role=msg.role, content=sanitize_prompt(msg.content)) for msg in request.messages
        ]

        logger.info(
            "ai.chat_started",
            provider=provider_name,
            model=model,
            tier=request.task_tier,
            message_count=len(messages),
        )

        # Resolve provider from registry
        registry = get_registry()

        # Try fallback chain if configured for this tier
        chain = get_fallback_chain(request.task_tier) if request.task_tier else None

        try:
            if chain and chain.has_fallbacks:
                result = await call_with_fallback(chain, registry, messages)
            else:
                provider = registry.get_llm(provider_name)
                result = await provider.complete(messages, model_override=model)
        except Exception as e:
            logger.error(
                "ai.chat_failed",
                exc_info=True,
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Chat completion failed") from e

        # Validate output
        content = validate_output(result.content)

        response_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

        usage = UsageInfo()
        if result.usage:
            usage = UsageInfo(
                prompt_tokens=result.usage.get("prompt_tokens", 0),
                completion_tokens=result.usage.get("completion_tokens", 0),
                total_tokens=result.usage.get("total_tokens", 0),
            )

        response = ChatCompletionResponse(
            id=response_id,
            created=int(time.time()),
            model=model_id,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="stop",
                )
            ],
            usage=usage,
        )

        logger.info(
            "ai.chat_completed",
            response_id=response_id,
            output_length=len(content),
            provider=provider_name,
            usage=result.usage,
        )

        return response

    async def stream_chat(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
        """Stream chat completion tokens as SSE-formatted strings.

        Yields SSE-formatted chunks compatible with OpenAI streaming format.

        Args:
            request: The chat completion request.

        Yields:
            SSE-formatted data strings (e.g., 'data: {"choices":[...]}\n\n').

        Raises:
            AIExecutionError: If the provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(request.task_tier)
        model_id = f"{provider_name}:{model}"
        response_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

        messages = [
            Message(role=msg.role, content=sanitize_prompt(msg.content)) for msg in request.messages
        ]

        logger.info(
            "ai.stream_started",
            provider=provider_name,
            model=model,
            tier=request.task_tier,
            message_count=len(messages),
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)
        timeout_seconds = settings.ai.stream_timeout_seconds

        try:
            async with asyncio.timeout(timeout_seconds):
                async for chunk in provider.stream(messages, model_override=model):  # type: ignore[attr-defined]
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

        except TimeoutError:
            logger.error(
                "ai.stream_timeout",
                response_id=response_id,
                provider=provider_name,
                timeout_seconds=timeout_seconds,
            )
            error_data = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_id,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "timeout"}],
            }
            yield f"data: {json.dumps(error_data)}\n\n"

        except Exception as e:
            logger.error(
                "ai.stream_failed",
                exc_info=True,
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Chat streaming failed") from e

        # Send final [DONE] sentinel (always, including after timeout)
        yield "data: [DONE]\n\n"

        logger.info(
            "ai.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# ── Module-level singleton ──

_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get or create the chat service singleton.

    Returns:
        Singleton ChatService instance.
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
