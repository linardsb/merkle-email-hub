"""Tests for fallback chains module (Phase 22.4)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.fallback import (
    FallbackChain,
    FallbackEntry,
    _is_retryable,
    call_with_fallback,
    parse_fallback_chains,
)
from app.ai.protocols import CompletionResponse, Message
from app.core.resilience import CircuitOpenError

# ── FallbackEntry tests ──


def test_parse_fallback_entry() -> None:
    entry = FallbackEntry.parse("anthropic:claude-opus-4-6")
    assert entry.provider == "anthropic"
    assert entry.model == "claude-opus-4-6"


def test_parse_fallback_entry_invalid() -> None:
    with pytest.raises(ValueError, match="must be 'provider:model'"):
        FallbackEntry.parse("no-colon")


def test_parse_fallback_entry_empty_provider() -> None:
    with pytest.raises(ValueError, match="Empty provider or model"):
        FallbackEntry.parse(":model")


def test_parse_fallback_entry_empty_model() -> None:
    with pytest.raises(ValueError, match="Empty provider or model"):
        FallbackEntry.parse("provider:")


# ── parse_fallback_chains tests ──


def test_parse_fallback_chains_empty() -> None:
    result = parse_fallback_chains({})
    assert result == {}


def test_parse_fallback_chains_skips_empty_tiers() -> None:
    result = parse_fallback_chains({"complex": [], "standard": ["openai:gpt-4o"]})
    assert "complex" not in result
    assert "standard" in result


def test_parse_fallback_chains_multiple_tiers() -> None:
    raw = {
        "complex": ["anthropic:claude-opus-4-6", "openai:gpt-4o"],
        "standard": ["anthropic:claude-sonnet-4-6", "openai:gpt-4o-mini"],
    }
    chains = parse_fallback_chains(raw)
    assert len(chains) == 2

    complex_chain = chains["complex"]
    assert complex_chain.tier == "complex"
    assert len(complex_chain.entries) == 2
    assert complex_chain.entries[0].provider == "anthropic"
    assert complex_chain.entries[1].provider == "openai"

    standard_chain = chains["standard"]
    assert standard_chain.tier == "standard"
    assert len(standard_chain.entries) == 2


# ── FallbackChain tests ──


def test_fallback_chain_primary() -> None:
    chain = FallbackChain(
        tier="complex",
        entries=(
            FallbackEntry(provider="anthropic", model="claude-opus-4-6"),
            FallbackEntry(provider="openai", model="gpt-4o"),
        ),
    )
    assert chain.primary.provider == "anthropic"
    assert chain.primary.model == "claude-opus-4-6"


def test_fallback_chain_has_fallbacks_single() -> None:
    chain = FallbackChain(
        tier="complex",
        entries=(FallbackEntry(provider="anthropic", model="claude-opus-4-6"),),
    )
    assert chain.has_fallbacks is False


def test_fallback_chain_has_fallbacks_multiple() -> None:
    chain = FallbackChain(
        tier="complex",
        entries=(
            FallbackEntry(provider="anthropic", model="claude-opus-4-6"),
            FallbackEntry(provider="openai", model="gpt-4o"),
        ),
    )
    assert chain.has_fallbacks is True


# ── _is_retryable tests ──


def test_is_retryable_timeout() -> None:
    assert _is_retryable(TimeoutError()) is True


def test_is_retryable_circuit_open() -> None:
    assert _is_retryable(CircuitOpenError("test")) is True


def test_is_retryable_value_error() -> None:
    assert _is_retryable(ValueError("bad input")) is False


def test_is_retryable_status_code_429() -> None:
    @dataclass
    class FakeError(Exception):
        status_code: int = 429

    assert _is_retryable(FakeError()) is True


def test_is_retryable_status_code_401() -> None:
    @dataclass
    class FakeError(Exception):
        status_code: int = 401

    assert _is_retryable(FakeError()) is False


# ── call_with_fallback tests ──


def _make_chain(n: int = 2) -> FallbackChain:
    entries: list[FallbackEntry] = []
    providers = [("anthropic", "claude-opus-4-6"), ("openai", "gpt-4o"), ("openai", "gpt-4o-mini")]
    for i in range(n):
        p, m = providers[i % len(providers)]
        entries.append(FallbackEntry(provider=p, model=m))
    return FallbackChain(tier="complex", entries=tuple(entries))


def _make_registry(side_effects: list[Any]) -> MagicMock:
    """Create a mock registry where get_llm returns providers with given side effects."""
    registry = MagicMock()
    call_index = 0

    def get_llm(name: str) -> MagicMock:
        nonlocal call_index
        provider = MagicMock()
        effect = side_effects[call_index] if call_index < len(side_effects) else None
        if isinstance(effect, Exception):
            provider.complete = AsyncMock(side_effect=effect)
        else:
            provider.complete = AsyncMock(return_value=effect)
        call_index += 1
        return provider

    registry.get_llm = MagicMock(side_effect=get_llm)
    return registry


def _make_response(content: str = "hello") -> CompletionResponse:
    return CompletionResponse(content=content, model="test-model", usage={"total_tokens": 10})


@pytest.mark.asyncio
async def test_call_with_fallback_primary_succeeds() -> None:
    chain = _make_chain(2)
    response = _make_response("primary response")
    registry = _make_registry([response])

    result = await call_with_fallback(chain, registry, [Message(role="user", content="hi")])
    assert result.content == "primary response"
    # Only one provider call made
    assert registry.get_llm.call_count == 1


@pytest.mark.asyncio
async def test_call_with_fallback_cascades_on_timeout() -> None:
    chain = _make_chain(2)
    response = _make_response("fallback response")
    registry = _make_registry([TimeoutError(), response])

    result = await call_with_fallback(chain, registry, [Message(role="user", content="hi")])
    assert result.content == "fallback response"
    assert registry.get_llm.call_count == 2


@pytest.mark.asyncio
async def test_call_with_fallback_cascades_on_circuit_open() -> None:
    chain = _make_chain(2)
    response = _make_response("fallback response")
    registry = _make_registry([CircuitOpenError("breaker open"), response])

    result = await call_with_fallback(chain, registry, [Message(role="user", content="hi")])
    assert result.content == "fallback response"


@pytest.mark.asyncio
async def test_call_with_fallback_all_fail() -> None:
    chain = _make_chain(2)
    registry = _make_registry([TimeoutError(), TimeoutError()])

    with pytest.raises(asyncio.TimeoutError):
        await call_with_fallback(chain, registry, [Message(role="user", content="hi")])


@pytest.mark.asyncio
async def test_call_with_fallback_non_retryable_raises_immediately() -> None:
    chain = _make_chain(2)
    registry = _make_registry([ValueError("bad request")])

    with pytest.raises(ValueError, match="bad request"):
        await call_with_fallback(chain, registry, [Message(role="user", content="hi")])
    # Only one provider call — did not try fallback
    assert registry.get_llm.call_count == 1


@pytest.mark.asyncio
async def test_call_with_fallback_logs_fallback_event(capsys: pytest.CaptureFixture[str]) -> None:
    chain = _make_chain(2)
    response = _make_response("ok")
    registry = _make_registry([TimeoutError(), response])

    await call_with_fallback(chain, registry, [Message(role="user", content="hi")])

    captured = capsys.readouterr()
    assert "fallback.cascading" in captured.out


@pytest.mark.asyncio
async def test_call_with_fallback_single_entry_no_cascade() -> None:
    chain = _make_chain(1)
    registry = _make_registry([TimeoutError()])

    with pytest.raises(asyncio.TimeoutError):
        await call_with_fallback(chain, registry, [Message(role="user", content="hi")])
    assert registry.get_llm.call_count == 1
