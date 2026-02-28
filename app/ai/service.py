"""Chat orchestration service using the LLMProvider protocol.

Provider-agnostic: resolves the configured provider from the registry
and delegates completion to it. Handles message extraction, provider
resolution, and OpenAI-compatible response formatting.
"""

import time
import uuid

from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
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

    Resolves the LLM provider from the registry based on configuration,
    converts between OpenAI-compatible schemas and protocol Message objects,
    and formats responses.
    """

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Process a chat completion request.

        Extracts messages, resolves the configured LLM provider,
        sends the completion request, and returns an OpenAI-compatible response.

        Args:
            request: The chat completion request with messages.

        Returns:
            ChatCompletionResponse with the provider's response.

        Raises:
            AIExecutionError: If the provider fails to generate a response.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model_id = f"{provider_name}:{settings.ai.model}"

        # Convert schema messages to protocol messages
        messages = [Message(role=msg.role, content=msg.content) for msg in request.messages]

        logger.info(
            "ai.chat_started",
            provider=provider_name,
            model=settings.ai.model,
            message_count=len(messages),
        )

        # Resolve provider from registry
        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages)
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
            raise AIExecutionError(f"Chat completion failed: {e}") from e

        response_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

        # Build usage info from provider response
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
                    message=ChatMessage(role="assistant", content=result.content),
                    finish_reason="stop",
                )
            ],
            usage=usage,
        )

        logger.info(
            "ai.chat_completed",
            response_id=response_id,
            output_length=len(result.content),
            provider=provider_name,
        )

        return response


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
