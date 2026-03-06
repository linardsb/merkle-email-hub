# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Native Anthropic SDK adapter for Claude models.

Uses the official anthropic Python SDK with async support.
Supports both single-shot completion and SSE streaming.
"""

from collections.abc import AsyncIterator
from typing import Any

from app.ai.exceptions import AIConfigurationError, AIExecutionError
from app.ai.protocols import CompletionResponse, Message
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_REQUEST_TIMEOUT = 120.0
_DEFAULT_MAX_TOKENS = 4096


class AnthropicProvider:
    """LLM provider using the native Anthropic SDK.

    Reads settings from Settings.ai at instantiation time:
    - ai.api_key: Anthropic API key (required)
    - ai.model: Model identifier (claude-opus-4-20250514, claude-sonnet-4-20250514, etc.)
    """

    def __init__(self) -> None:
        """Initialize the provider from application settings.

        Raises:
            AIConfigurationError: If the anthropic package is not installed
                or AI__API_KEY is not configured.
        """
        try:
            import anthropic
        except ImportError as e:
            raise AIConfigurationError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from e

        settings = get_settings()
        self._model = settings.ai.model
        api_key = settings.ai.api_key

        if not api_key:
            raise AIConfigurationError(
                "AI__API_KEY is required for Anthropic provider. "
                "Set it via environment variable or .env file."
            )

        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=_REQUEST_TIMEOUT,
        )

        logger.info(
            "ai.provider.anthropic_initialized",
            model=self._model,
        )

    async def complete(self, messages: list[Message], **kwargs: object) -> CompletionResponse:
        """Send a chat completion request via Anthropic SDK.

        Args:
            messages: Conversation history as Message objects.
            **kwargs: Additional parameters. Supports model_override, max_tokens,
                temperature, top_p, stop_sequences.

        Returns:
            CompletionResponse with generated content and usage statistics.

        Raises:
            AIConfigurationError: If authentication fails.
            AIExecutionError: If the API call fails or times out.
        """
        import anthropic

        # Anthropic requires system message separate from messages
        system_text = ""
        chat_messages: list[dict[str, str]] = []
        for m in messages:
            if m.role == "system":
                system_text += m.content + "\n"
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        # Build kwargs for Anthropic API
        model = str(kwargs.get("model_override", self._model))
        api_kwargs: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": int(str(kwargs.get("max_tokens", _DEFAULT_MAX_TOKENS))),
        }
        if system_text.strip():
            api_kwargs["system"] = system_text.strip()

        for key in ("temperature", "top_p", "stop_sequences"):
            if key in kwargs:
                api_kwargs[key] = kwargs[key]

        logger.debug(
            "ai.provider.completion_started",
            model=model,
            message_count=len(chat_messages),
        )

        try:
            response = await self._client.messages.create(**api_kwargs)
        except anthropic.APITimeoutError as e:
            msg = f"Anthropic API request timed out after {_REQUEST_TIMEOUT}s"
            logger.error("ai.provider.completion_timeout", model=model)
            raise AIExecutionError(msg) from e
        except anthropic.RateLimitError as e:
            msg = "Anthropic API rate limit exceeded"
            logger.error("ai.provider.completion_rate_limited", model=model)
            raise AIExecutionError(msg) from e
        except anthropic.AuthenticationError as e:
            msg = "AI provider authentication failed"
            logger.error("ai.provider.completion_auth_failed")
            raise AIConfigurationError(msg) from e
        except anthropic.APIError as e:
            msg = "AI provider request failed"
            logger.error(
                "ai.provider.completion_failed",
                model=model,
                status_code=getattr(e, "status_code", None),
                detail=str(e.message),
            )
            raise AIExecutionError(msg) from e

        # Extract text content from response
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        usage: dict[str, int] = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        logger.info(
            "ai.provider.completion_completed",
            model=response.model,
            content_length=len(content),
            usage=usage,
        )

        return CompletionResponse(
            content=content,
            model=response.model,
            usage=usage,
        )

    async def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[str]:
        """Stream completion tokens via Anthropic SDK.

        Args:
            messages: Conversation history as Message objects.
            **kwargs: Additional parameters. Supports model_override, max_tokens,
                temperature, top_p, stop_sequences.

        Yields:
            Individual text chunks as they are generated.

        Raises:
            AIExecutionError: If the API call fails.
        """
        import anthropic

        system_text = ""
        chat_messages: list[dict[str, str]] = []
        for m in messages:
            if m.role == "system":
                system_text += m.content + "\n"
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        model = str(kwargs.get("model_override", self._model))
        api_kwargs: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": int(str(kwargs.get("max_tokens", _DEFAULT_MAX_TOKENS))),
        }
        if system_text.strip():
            api_kwargs["system"] = system_text.strip()

        for key in ("temperature", "top_p", "stop_sequences"):
            if key in kwargs:
                api_kwargs[key] = kwargs[key]

        logger.debug(
            "ai.provider.stream_started",
            model=model,
            message_count=len(chat_messages),
        )

        try:
            async with self._client.messages.stream(**api_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.APITimeoutError as e:
            msg = f"Anthropic streaming timed out after {_REQUEST_TIMEOUT}s"
            logger.error("ai.provider.stream_timeout", model=model)
            raise AIExecutionError(msg) from e
        except anthropic.APIError as e:
            msg = "AI provider streaming failed"
            logger.error("ai.provider.stream_failed", model=model)
            raise AIExecutionError(msg) from e

        logger.debug("ai.provider.stream_completed", model=model)

    async def close(self) -> None:
        """Close the underlying HTTP client.

        Should be called during application shutdown to release connections.
        """
        try:
            await self._client.close()
        except RuntimeError:
            pass  # Event loop already closed during shutdown
