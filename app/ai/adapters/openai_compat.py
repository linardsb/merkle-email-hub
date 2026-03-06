"""OpenAI-compatible LLM provider using raw httpx.

Works with any API that implements the OpenAI Chat Completions format:
- OpenAI (api.openai.com)
- Anthropic via OpenAI-compatible proxy
- Ollama (localhost:11434/v1)
- vLLM (localhost:8000/v1)
- LiteLLM (localhost:4000/v1)
- Any OpenRouter, Together AI, Groq endpoint

Uses httpx.AsyncClient for non-blocking HTTP calls with connection pooling.
Reads configuration from app.core.config.Settings.ai namespace.
"""

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.ai.exceptions import AIConfigurationError, AIExecutionError
from app.ai.protocols import CompletionResponse, Message
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default base URL when none is configured (OpenAI)
_DEFAULT_BASE_URL = "https://api.openai.com/v1"

# Timeout for LLM API calls (seconds)
_REQUEST_TIMEOUT = 120.0


class OpenAICompatProvider:
    """LLM provider for OpenAI-compatible Chat Completions APIs.

    Reads settings from `Settings.ai` at instantiation time:
    - ai.api_key: Bearer token for authentication
    - ai.base_url: API base URL (defaults to OpenAI)
    - ai.model: Model identifier for the completion request

    The provider creates its own httpx.AsyncClient per instance. For
    long-lived usage (e.g., in ChatService), prefer holding a single
    provider instance and calling close() on shutdown.
    """

    def __init__(self) -> None:
        """Initialize the provider from application settings.

        Raises:
            AIConfigurationError: If no API key is configured and base_url
                requires authentication (i.e., not a local endpoint).
        """
        settings = get_settings()
        self._model = settings.ai.model
        self._base_url = (settings.ai.base_url or _DEFAULT_BASE_URL).rstrip("/")
        self._api_key = settings.ai.api_key

        # Local endpoints (Ollama, vLLM) don't need API keys
        is_local = any(
            host in self._base_url
            for host in ("localhost", "127.0.0.1", "0.0.0.0")  # noqa: S104
        )
        if not self._api_key and not is_local:
            msg = (
                f"AI__API_KEY is required for remote endpoint '{self._base_url}'. "
                "Set it via environment variable or .env file."
            )
            raise AIConfigurationError(msg)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=httpx.Timeout(_REQUEST_TIMEOUT),
        )

        logger.info(
            "ai.provider.openai_compat_initialized",
            model=self._model,
            base_url=self._base_url,
        )

    async def complete(self, messages: list[Message], **kwargs: object) -> CompletionResponse:
        """Send a chat completion request to the OpenAI-compatible API.

        Args:
            messages: Conversation history as Message objects.
            **kwargs: Additional parameters passed to the API (temperature,
                max_tokens, top_p, etc.).

        Returns:
            CompletionResponse with generated content and usage statistics.

        Raises:
            AIExecutionError: If the API call fails or returns an error.
        """
        payload: dict[str, Any] = {
            "model": kwargs.get("model_override", self._model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }

        # Pass through supported kwargs
        for key in (
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "presence_penalty",
            "frequency_penalty",
        ):
            if key in kwargs:
                payload[key] = kwargs[key]

        logger.debug(
            "ai.provider.completion_started",
            model=self._model,
            message_count=len(messages),
        )

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as e:
            msg = f"LLM API request timed out after {_REQUEST_TIMEOUT}s"
            logger.error("ai.provider.completion_timeout", model=self._model, error=str(e))
            raise AIExecutionError(msg) from e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            detail = e.response.text[:500]
            msg = "LLM API request failed"
            logger.error(
                "ai.provider.completion_http_error",
                model=self._model,
                status_code=status_code,
                detail=detail,
            )
            raise AIExecutionError(msg) from e
        except httpx.HTTPError as e:
            msg = "LLM API request failed"
            logger.error("ai.provider.completion_failed", model=self._model, error=str(e))
            raise AIExecutionError(msg) from e

        data: dict[str, Any] = response.json()

        # Extract response content
        choices = data.get("choices", [])
        if not choices:
            msg = "LLM API returned empty choices"
            raise AIExecutionError(msg)

        content: str = choices[0].get("message", {}).get("content", "")
        model_name: str = data.get("model", self._model)

        # Extract usage if present
        usage: dict[str, int] | None = None
        usage_data = data.get("usage")
        if usage_data:
            usage = {
                "prompt_tokens": int(usage_data.get("prompt_tokens", 0)),
                "completion_tokens": int(usage_data.get("completion_tokens", 0)),
                "total_tokens": int(usage_data.get("total_tokens", 0)),
            }

        logger.info(
            "ai.provider.completion_completed",
            model=model_name,
            content_length=len(content),
            usage=usage,
        )

        return CompletionResponse(content=content, model=model_name, usage=usage)

    async def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[str]:
        """Stream completion tokens from the OpenAI-compatible API.

        Uses server-sent events (SSE) streaming. Each chunk yields
        the delta content as a string.

        Args:
            messages: Conversation history as Message objects.
            **kwargs: Additional parameters passed to the API.

        Yields:
            Individual text chunks as they are generated.

        Raises:
            AIExecutionError: If the API call fails.
        """
        payload: dict[str, Any] = {
            "model": kwargs.get("model_override", self._model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }

        for key in ("temperature", "max_tokens", "top_p", "stop"):
            if key in kwargs:
                payload[key] = kwargs[key]

        logger.debug(
            "ai.provider.stream_started",
            model=self._model,
            message_count=len(messages),
        )

        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]  # Strip "data: " prefix
                    if data_str.strip() == "[DONE]":
                        break

                    import json

                    try:
                        chunk: dict[str, Any] = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            msg = f"LLM streaming API returned {status_code}"
            logger.error(
                "ai.provider.stream_http_error", model=self._model, status_code=status_code
            )
            raise AIExecutionError(msg) from e
        except httpx.HTTPError as e:
            msg = "LLM streaming request failed"
            logger.error("ai.provider.stream_failed", model=self._model, error=str(e))
            raise AIExecutionError(msg) from e

        logger.debug("ai.provider.stream_completed", model=self._model)

    async def close(self) -> None:
        """Close the underlying HTTP client.

        Should be called during application shutdown to release connections.
        """
        try:
            await self._client.aclose()
        except RuntimeError:
            pass  # Event loop already closed during shutdown
