"""Tests for LLM streaming response timeout."""

import asyncio
import json
from collections.abc import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest

from app.ai.service import ChatService


async def _fast_stream(*_args: object, **_kwargs: object) -> AsyncIterator[str]:
    """Mock stream that yields two chunks quickly."""
    yield "Hello"
    yield " world"


async def _hanging_stream(*_args: object, **_kwargs: object) -> AsyncIterator[str]:
    """Mock stream that hangs forever after one chunk."""
    yield "partial"
    await asyncio.sleep(9999)


def _mock_provider(stream_fn: object) -> MagicMock:
    provider = MagicMock()
    provider.stream = stream_fn
    return provider


def _mock_request() -> MagicMock:
    req = MagicMock()
    req.messages = [MagicMock(role="user", content="test")]
    req.task_tier = ""
    req.stream = True
    return req


@pytest.mark.asyncio
async def test_stream_completes_within_timeout() -> None:
    service = ChatService()
    request = _mock_request()

    with (
        patch("app.ai.service.get_settings") as mock_settings,
        patch("app.ai.service.get_registry") as mock_registry,
        patch("app.ai.service.sanitize_prompt", side_effect=lambda x: x),
    ):
        settings = mock_settings.return_value
        settings.ai.provider = "openai"
        settings.ai.stream_timeout_seconds = 10

        provider = _mock_provider(_fast_stream)
        mock_registry.return_value.get_llm.return_value = provider

        chunks: list[str] = []
        async for chunk in service.stream_chat(request):
            chunks.append(chunk)

    # Should have content chunks + [DONE]
    assert any("[DONE]" in c for c in chunks)
    content_chunks = [c for c in chunks if "delta" in c and "content" in c]
    assert len(content_chunks) == 2


@pytest.mark.asyncio
async def test_stream_times_out() -> None:
    service = ChatService()
    request = _mock_request()

    with (
        patch("app.ai.service.get_settings") as mock_settings,
        patch("app.ai.service.get_registry") as mock_registry,
        patch("app.ai.service.sanitize_prompt", side_effect=lambda x: x),
    ):
        settings = mock_settings.return_value
        settings.ai.provider = "openai"
        settings.ai.stream_timeout_seconds = 0.1  # Very short timeout

        provider = _mock_provider(_hanging_stream)
        mock_registry.return_value.get_llm.return_value = provider

        chunks: list[str] = []
        async for chunk in service.stream_chat(request):
            chunks.append(chunk)

    # Should have: partial content, timeout error, [DONE]
    timeout_chunks = [c for c in chunks if "timeout" in c]
    assert len(timeout_chunks) == 1

    # Parse the timeout chunk
    timeout_data = json.loads(timeout_chunks[0].replace("data: ", "").strip())
    assert timeout_data["choices"][0]["finish_reason"] == "timeout"

    # [DONE] sentinel always sent
    assert any("[DONE]" in c for c in chunks)
