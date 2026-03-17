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

    def _apply_token_budget(
        self, messages: list[Message], kwargs: dict[str, object]
    ) -> list[Message]:
        """Trim messages to fit token budget if enabled."""
        settings = get_settings()
        if not settings.ai.token_budget_enabled:
            return messages
        from app.ai.token_budget import TokenBudgetManager

        model = str(kwargs.get("model_override", self._model))
        budget_mgr = TokenBudgetManager(
            model=model,
            reserve_tokens=settings.ai.token_budget_reserve,
            max_context_tokens=settings.ai.token_budget_max,
        )
        return budget_mgr.trim_to_budget(messages)

    async def _check_cost_budget(self) -> None:
        """Check budget before making an API call. Raises BudgetExceededError if over budget."""
        settings = get_settings()
        if not settings.ai.cost_governor_enabled:
            return
        from app.ai.cost_governor import BudgetStatus, get_cost_governor

        governor = get_cost_governor()
        status = await governor.check_budget()
        if status == BudgetStatus.EXCEEDED:
            from app.ai.exceptions import BudgetExceededError

            raise BudgetExceededError("Monthly AI budget exceeded")

    async def _report_cost(
        self, model: str, usage: dict[str, int] | None, kwargs: dict[str, object]
    ) -> None:
        """Report token usage to cost governor if enabled. Fire-and-forget."""
        settings = get_settings()
        if not settings.ai.cost_governor_enabled or usage is None:
            return
        try:
            from app.ai.cost_governor import get_cost_governor

            governor = get_cost_governor()
            await governor.record(
                model=model,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                agent=str(kwargs.get("agent_name", "")),
                project_id=str(kwargs.get("project_id", "")),
            )
        except Exception:
            logger.debug("cost_governor.report_failed", model=model)

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

        # Token budget trimming (Phase 22.3)
        messages = self._apply_token_budget(messages, dict(kwargs))

        # Cost budget check (Phase 22.5)
        await self._check_cost_budget()

        # Anthropic requires system message separate from messages
        system_parts: list[dict[str, Any]] = []
        has_cache_control = False
        chat_messages: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                block: dict[str, Any] = {"type": "text", "text": m.content}
                if m.cache_control:
                    block["cache_control"] = m.cache_control
                    has_cache_control = True
                system_parts.append(block)
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        # Build kwargs for Anthropic API
        model = str(kwargs.get("model_override", self._model))
        api_kwargs: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": int(str(kwargs.get("max_tokens", _DEFAULT_MAX_TOKENS))),
        }
        if system_parts:
            if has_cache_control:
                # Structured content blocks for cache control
                api_kwargs["system"] = system_parts
            else:
                # Plain string for backward compatibility
                api_kwargs["system"] = "\n".join(p["text"] for p in system_parts).strip()

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
            block_any: Any = block
            if block_any.type == "text":
                content += block_any.text

        usage: dict[str, int] = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        # Track cache metrics when available
        cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        if cache_creation or cache_read:
            usage["cache_creation_input_tokens"] = cache_creation
            usage["cache_read_input_tokens"] = cache_read

        logger.info(
            "ai.provider.completion_completed",
            model=response.model,
            content_length=len(content),
            usage=usage,
            cache_read=cache_read,
            cache_creation=cache_creation,
        )

        # Cost tracking (Phase 22.5)
        await self._report_cost(response.model, usage, dict(kwargs))

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

        # Token budget trimming (Phase 22.3)
        messages = self._apply_token_budget(messages, dict(kwargs))

        system_parts_s: list[dict[str, Any]] = []
        has_cache_s = False
        chat_messages: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                block_s: dict[str, Any] = {"type": "text", "text": m.content}
                if m.cache_control:
                    block_s["cache_control"] = m.cache_control
                    has_cache_s = True
                system_parts_s.append(block_s)
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        model = str(kwargs.get("model_override", self._model))
        api_kwargs: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": int(str(kwargs.get("max_tokens", _DEFAULT_MAX_TOKENS))),
        }
        if system_parts_s:
            if has_cache_s:
                api_kwargs["system"] = system_parts_s
            else:
                api_kwargs["system"] = "\n".join(p["text"] for p in system_parts_s).strip()

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
