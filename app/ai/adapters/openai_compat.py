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

import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.ai.exceptions import AIConfigurationError, AIExecutionError
from app.ai.multimodal import (
    AudioBlock,
    ContentBlock,
    ImageBlock,
    StructuredOutputBlock,
    TextBlock,
    ToolResultBlock,
    normalize_content,
    validate_content_blocks,
)
from app.ai.protocols import CompletionResponse, Message
from app.core.config import get_settings
from app.core.credentials import CredentialLease, CredentialPool
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

        # Credential pool (Phase 46.2)
        # isinstance guard prevents MagicMock in tests from triggering pool init
        self._pool: CredentialPool | None = None
        provider_service = settings.ai.provider
        if (
            settings.credentials.enabled
            and isinstance(settings.credentials.pools, dict)  # pyright: ignore[reportUnnecessaryIsInstance] — guards against MagicMock in tests
            and provider_service in settings.credentials.pools
        ):
            from app.core.credentials import get_credential_pool

            self._pool = get_credential_pool(provider_service)
            self._api_key: str | None = None
        else:
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
            pool=self._pool is not None,
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

    @staticmethod
    def _extract_structured_output(
        messages: list[Message],
    ) -> StructuredOutputBlock | None:
        """Extract StructuredOutputBlock from the last message, if present."""
        if not messages:
            return None
        last = messages[-1]
        if isinstance(last.content, list):
            for block in last.content:
                if isinstance(block, StructuredOutputBlock):
                    return block
        return None

    def _check_vision_capability(self, model: str) -> bool:
        """Check if the model supports vision via capability registry."""
        try:
            from app.ai.capability_registry import ModelCapability, get_capability_registry

            registry = get_capability_registry()
            spec = registry.get(model)
            if spec is None:
                return True  # Unknown model — assume capable (fail at API level)
            return ModelCapability.VISION in spec.capabilities
        except Exception:
            return True  # Registry unavailable — don't block

    def _build_messages_payload(
        self,
        messages: list[Message],
        model: str,
    ) -> list[dict[str, Any]]:
        """Build OpenAI messages payload with vision capability check."""
        has_vision = self._check_vision_capability(model)

        result: list[dict[str, Any]] = []
        for m in messages:
            blocks = normalize_content(m.content)
            validate_content_blocks(blocks)
            if not has_vision:
                # Replace images with text descriptions for non-vision models
                blocks = [
                    TextBlock(text=f"[Image: {b.media_type}, {len(b.data)} bytes]")
                    if isinstance(b, ImageBlock)
                    else b
                    for b in blocks
                ]
            content = self._serialize_content_blocks(blocks)
            result.append({"role": m.role, "content": content})
        return result

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
        # Token budget trimming (Phase 22.3)
        messages = self._apply_token_budget(messages, dict(kwargs))

        # Cost budget check (Phase 22.5)
        await self._check_cost_budget()

        model = str(kwargs.get("model_override", self._model))

        payload: dict[str, Any] = {
            "model": model,
            "messages": self._build_messages_payload(messages, model),
        }

        # Structured output via response_format (Phase 23.2)
        structured_block = self._extract_structured_output(messages)
        if structured_block:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": structured_block.name,
                    "schema": structured_block.schema,
                    "strict": structured_block.strict,
                },
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
            model=model,
            message_count=len(messages),
        )

        lease: CredentialLease | None = None
        request_headers: dict[str, str] | None = None
        try:
            if self._pool:
                lease = await self._pool.get_key()
                request_headers = {"Authorization": f"Bearer {lease.key}"}

            response = await self._client.post(
                "/chat/completions",
                json=payload,
                headers=request_headers,
            )
            response.raise_for_status()

            if lease:
                await lease.report_success()
        except httpx.TimeoutException as e:
            msg = f"LLM API request timed out after {_REQUEST_TIMEOUT}s"
            logger.error("ai.provider.completion_timeout", model=self._model, error=str(e))
            raise AIExecutionError(msg) from e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if lease:
                await lease.report_failure(status_code)
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
            if lease:
                await lease.report_failure(500)
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

        # Parse structured output if present
        parsed: dict[str, object] | None = None
        if structured_block and content:
            try:
                parsed = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                logger.debug("ai.provider.structured_output_parse_failed", model=model_name)

        logger.info(
            "ai.provider.completion_completed",
            model=model_name,
            content_length=len(content),
            usage=usage,
        )

        # Cost tracking (Phase 22.5)
        await self._report_cost(model_name, usage, dict(kwargs))

        return CompletionResponse(
            content=content,
            model=model_name,
            usage=usage,
            parsed=parsed,
        )

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
        # Token budget trimming (Phase 22.3)
        messages = self._apply_token_budget(messages, dict(kwargs))

        model = str(kwargs.get("model_override", self._model))

        payload: dict[str, Any] = {
            "model": model,
            "messages": self._build_messages_payload(messages, model),
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

        lease: CredentialLease | None = None
        request_headers: dict[str, str] | None = None
        try:
            if self._pool:
                lease = await self._pool.get_key()
                request_headers = {"Authorization": f"Bearer {lease.key}"}

            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=payload,
                headers=request_headers,
            ) as response:
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

            if lease:
                await lease.report_success()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if lease:
                await lease.report_failure(status_code)
            msg = f"LLM streaming API returned {status_code}"
            logger.error(
                "ai.provider.stream_http_error", model=self._model, status_code=status_code
            )
            raise AIExecutionError(msg) from e
        except httpx.HTTPError as e:
            if lease:
                await lease.report_failure(500)
            msg = "LLM streaming request failed"
            logger.error("ai.provider.stream_failed", model=self._model, error=str(e))
            raise AIExecutionError(msg) from e

        logger.debug("ai.provider.stream_completed", model=self._model)

    @staticmethod
    def _serialize_content_blocks(
        blocks: list[ContentBlock],
    ) -> str | list[dict[str, Any]]:
        """Serialize content blocks to OpenAI API format."""
        import base64 as b64mod

        # Fast path: single text block → plain string
        if len(blocks) == 1 and isinstance(blocks[0], TextBlock):
            return blocks[0].text

        result: list[dict[str, Any]] = []
        for b in blocks:
            if isinstance(b, TextBlock):
                result.append({"type": "text", "text": b.text})
            elif isinstance(b, ImageBlock):
                if b.source == "base64":
                    data_uri = (
                        f"data:{b.media_type};base64,{b64mod.b64encode(b.data).decode('ascii')}"
                    )
                    result.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        }
                    )
                elif b.source == "url":
                    result.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": b.url},
                        }
                    )
            elif isinstance(b, AudioBlock):
                # OpenAI doesn't support audio in chat completions — placeholder
                result.append(
                    {
                        "type": "text",
                        "text": f"[Audio: {b.media_type}, {len(b.data)} bytes]",
                    }
                )
            elif isinstance(b, ToolResultBlock):
                # OpenAI tool results go in a separate message with role=tool
                nested = OpenAICompatProvider._serialize_content_blocks(b.content)
                text = (
                    nested
                    if isinstance(nested, str)
                    else " ".join(p.get("text", "") for p in nested if p.get("type") == "text")
                )
                result.append({"type": "text", "text": text})
            elif isinstance(b, StructuredOutputBlock):  # pyright: ignore[reportUnnecessaryIsInstance]
                pass  # Handled via response_format, not content blocks
        return result

    async def close(self) -> None:
        """Close the underlying HTTP client.

        Should be called during application shutdown to release connections.
        """
        with contextlib.suppress(RuntimeError):
            await self._client.aclose()
