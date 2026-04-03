# pyright: reportUnknownMemberType=false
"""Tests for LLM provider key rotation via CredentialPool (Phase 46.2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.ai.fallback import _is_retryable
from app.ai.protocols import Message
from app.core.credentials import CredentialLease, CredentialPool
from app.core.exceptions import NoHealthyCredentialsError


def _mock_settings(
    *,
    pool_enabled: bool = True,
    pools: dict[str, list[str]] | None = None,
    provider: str = "anthropic",
) -> MagicMock:
    """Build mock settings for provider init."""
    settings = MagicMock()
    settings.ai.model = "claude-sonnet-4-20250514"
    settings.ai.api_key = "sk-fallback"
    settings.ai.base_url = "https://api.openai.com/v1"
    settings.ai.provider = provider
    settings.ai.token_budget_enabled = False
    settings.ai.cost_governor_enabled = False
    settings.credentials.enabled = pool_enabled
    settings.credentials.pools = pools or {"anthropic": ["sk-1", "sk-2"]}
    return settings


def _make_lease(
    pool: CredentialPool | AsyncMock,
    key: str = "sk-1",
    key_hash: str = "hash1",
    service: str = "anthropic",
) -> CredentialLease:
    """Create a CredentialLease wired to a mock pool."""
    return CredentialLease(service=service, key=key, key_hash=key_hash, _pool=pool)


def _mock_anthropic_response() -> MagicMock:
    """Create a mock Anthropic API response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="ok")]
    usage = MagicMock()
    usage.input_tokens = 10
    usage.output_tokens = 5
    usage.cache_creation_input_tokens = None
    usage.cache_read_input_tokens = None
    mock_response.usage = usage
    mock_response.model = "claude-sonnet-4-20250514"
    return mock_response


# ── Anthropic Provider Tests ──


class TestAnthropicPoolDisabled:
    """Pool disabled → existing single-key behavior."""

    @pytest.mark.asyncio
    async def test_anthropic_pool_disabled_uses_single_key(self) -> None:
        settings = _mock_settings(pool_enabled=False)

        with (
            patch("app.ai.adapters.anthropic.get_settings", return_value=settings),
            patch("anthropic.AsyncAnthropic") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=_mock_anthropic_response())
            mock_cls.return_value = mock_client

            from app.ai.adapters.anthropic import AnthropicProvider

            provider = AnthropicProvider()
            assert provider._pool is None

            msg = Message(role="user", content="test")
            result = await provider.complete([msg])
            assert result.content == "ok"
            mock_client.messages.create.assert_awaited_once()


class TestAnthropicPoolRotation:
    """Pool enabled → keys rotated across calls."""

    @pytest.mark.asyncio
    async def test_anthropic_pool_rotates_keys(self) -> None:
        pool = AsyncMock(spec=CredentialPool)
        lease1 = _make_lease(pool, key="sk-1", key_hash="hash1")
        lease2 = _make_lease(pool, key="sk-2", key_hash="hash2")
        pool.get_key = AsyncMock(side_effect=[lease1, lease2])

        settings = _mock_settings()

        with (
            patch("app.ai.adapters.anthropic.get_settings", return_value=settings),
            patch(
                "app.core.credentials.get_credential_pool",
                return_value=pool,
            ),
            patch("anthropic.AsyncAnthropic") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=_mock_anthropic_response())
            mock_cls.return_value = mock_client

            from app.ai.adapters.anthropic import AnthropicProvider

            provider = AnthropicProvider()
            assert provider._pool is pool

            msg = Message(role="user", content="test")
            await provider.complete([msg])
            await provider.complete([msg])

            assert pool.get_key.await_count == 2
            # Both leases reported success via pool._record_success
            assert pool._record_success.await_count == 2
            pool._record_success.assert_any_await("hash1")
            pool._record_success.assert_any_await("hash2")
            # Client cache should have 2 entries
            assert len(provider._client_cache) == 2


class TestAnthropicPoolErrors:
    """Error handling with pool-enabled Anthropic provider."""

    @pytest.mark.asyncio
    async def test_anthropic_rate_limit_reports_failure(self) -> None:
        import anthropic

        pool = AsyncMock(spec=CredentialPool)
        lease = _make_lease(pool)
        pool.get_key = AsyncMock(return_value=lease)

        settings = _mock_settings()

        with (
            patch("app.ai.adapters.anthropic.get_settings", return_value=settings),
            patch("app.core.credentials.get_credential_pool", return_value=pool),
            patch("anthropic.AsyncAnthropic") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_http_response = MagicMock()
            mock_http_response.status_code = 429
            mock_http_response.json.return_value = {"error": {"message": "rate limited"}}
            mock_client.messages.create = AsyncMock(
                side_effect=anthropic.RateLimitError(
                    message="rate limited",
                    response=mock_http_response,
                    body={"error": {"message": "rate limited"}},
                ),
            )
            mock_cls.return_value = mock_client

            from app.ai.adapters.anthropic import AnthropicProvider
            from app.ai.exceptions import AIExecutionError

            provider = AnthropicProvider()

            msg = Message(role="user", content="test")
            with pytest.raises(AIExecutionError, match="rate limit"):
                await provider.complete([msg])

            pool._record_failure.assert_awaited_once_with("hash1", 429)

    @pytest.mark.asyncio
    async def test_anthropic_auth_error_reports_failure(self) -> None:
        import anthropic

        pool = AsyncMock(spec=CredentialPool)
        lease = _make_lease(pool)
        pool.get_key = AsyncMock(return_value=lease)

        settings = _mock_settings()

        with (
            patch("app.ai.adapters.anthropic.get_settings", return_value=settings),
            patch("app.core.credentials.get_credential_pool", return_value=pool),
            patch("anthropic.AsyncAnthropic") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_http_response = MagicMock()
            mock_http_response.status_code = 401
            mock_http_response.json.return_value = {"error": {"message": "invalid key"}}
            mock_client.messages.create = AsyncMock(
                side_effect=anthropic.AuthenticationError(
                    message="invalid key",
                    response=mock_http_response,
                    body={"error": {"message": "invalid key"}},
                ),
            )
            mock_cls.return_value = mock_client

            from app.ai.adapters.anthropic import AnthropicProvider
            from app.ai.exceptions import AIConfigurationError

            provider = AnthropicProvider()

            msg = Message(role="user", content="test")
            with pytest.raises(AIConfigurationError, match="authentication"):
                await provider.complete([msg])

            pool._record_failure.assert_awaited_once_with("hash1", 401)


class TestAnthropicStreamRotation:
    """Stream method uses rotated key."""

    @pytest.mark.asyncio
    async def test_stream_uses_rotated_key(self) -> None:
        pool = AsyncMock(spec=CredentialPool)
        lease = _make_lease(pool)
        pool.get_key = AsyncMock(return_value=lease)

        settings = _mock_settings()

        with (
            patch("app.ai.adapters.anthropic.get_settings", return_value=settings),
            patch("app.core.credentials.get_credential_pool", return_value=pool),
            patch("anthropic.AsyncAnthropic") as mock_cls,
        ):
            mock_client = AsyncMock()

            class MockTextStream:
                def __init__(self) -> None:
                    self._items = ["chunk1", "chunk2"]
                    self._index = 0

                def __aiter__(self) -> MockTextStream:
                    return self

                async def __anext__(self) -> str:
                    if self._index >= len(self._items):
                        raise StopAsyncIteration
                    item = self._items[self._index]
                    self._index += 1
                    return item

            mock_stream_ctx = MagicMock()
            mock_stream_ctx.text_stream = MockTextStream()

            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_client.messages.stream = MagicMock(return_value=mock_cm)
            mock_cls.return_value = mock_client

            from app.ai.adapters.anthropic import AnthropicProvider

            provider = AnthropicProvider()

            msg = Message(role="user", content="test")
            chunks: list[str] = []
            async for chunk in provider.stream([msg]):
                chunks.append(chunk)

            pool.get_key.assert_awaited_once()
            pool._record_success.assert_awaited_once_with("hash1")
            assert chunks == ["chunk1", "chunk2"]


# ── OpenAI-compat Provider Tests ──


class TestOpenAIPoolRotation:
    """Pool enabled → Authorization header rotated per request."""

    @pytest.mark.asyncio
    async def test_openai_pool_rotates_keys(self) -> None:
        pool = AsyncMock(spec=CredentialPool)
        lease1 = _make_lease(pool, key="sk-proj-1", key_hash="h1", service="openai")
        lease2 = _make_lease(pool, key="sk-proj-2", key_hash="h2", service="openai")
        pool.get_key = AsyncMock(side_effect=[lease1, lease2])

        settings = _mock_settings(pools={"openai": ["sk-proj-1", "sk-proj-2"]}, provider="openai")

        with (
            patch("app.ai.adapters.openai_compat.get_settings", return_value=settings),
            patch("app.core.credentials.get_credential_pool", return_value=pool),
        ):
            from app.ai.adapters.openai_compat import OpenAICompatProvider

            provider = OpenAICompatProvider()
            assert provider._pool is pool

            # Mock httpx client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "hello"}}],
                "model": "gpt-4o",
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            }
            mock_response.raise_for_status = MagicMock()
            provider._client.post = AsyncMock(return_value=mock_response)

            msg = Message(role="user", content="test")
            await provider.complete([msg])
            await provider.complete([msg])

            assert pool.get_key.await_count == 2
            # Verify Authorization headers were passed per-request
            calls = provider._client.post.call_args_list
            assert calls[0].kwargs["headers"] == {"Authorization": "Bearer sk-proj-1"}
            assert calls[1].kwargs["headers"] == {"Authorization": "Bearer sk-proj-2"}


class TestOpenAIPoolErrors:
    """Error handling with pool-enabled OpenAI provider."""

    @pytest.mark.asyncio
    async def test_openai_http_error_reports_failure(self) -> None:
        pool = AsyncMock(spec=CredentialPool)
        lease = _make_lease(pool, key="sk-proj-1", key_hash="h1", service="openai")
        pool.get_key = AsyncMock(return_value=lease)

        settings = _mock_settings(pools={"openai": ["sk-proj-1"]}, provider="openai")

        with (
            patch("app.ai.adapters.openai_compat.get_settings", return_value=settings),
            patch("app.core.credentials.get_credential_pool", return_value=pool),
        ):
            from app.ai.adapters.openai_compat import OpenAICompatProvider
            from app.ai.exceptions import AIExecutionError

            provider = OpenAICompatProvider()

            mock_response = httpx.Response(
                status_code=429,
                request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
            )
            provider._client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    message="rate limited",
                    request=mock_response.request,
                    response=mock_response,
                ),
            )

            msg = Message(role="user", content="test")
            with pytest.raises(AIExecutionError, match="LLM API request failed"):
                await provider.complete([msg])

            pool._record_failure.assert_awaited_once_with("h1", 429)


# ── Fallback Chain Integration ──


class TestFallbackChainIntegration:
    """NoHealthyCredentialsError triggers fallback to next provider."""

    def test_pool_exhausted_triggers_fallback(self) -> None:
        error = NoHealthyCredentialsError("anthropic")
        assert _is_retryable(error) is True

    def test_regular_auth_error_not_retryable(self) -> None:
        """Verify non-pool auth errors remain non-retryable."""

        class FakeAuthError(Exception):
            status_code = 401

        assert _is_retryable(FakeAuthError()) is False
