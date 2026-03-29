"""Fallback chains for provider resilience.

Ordered model fallbacks per tier. When the primary model fails with a
retryable error (timeout, rate limit, server error, circuit open),
the next model in the chain is tried automatically.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.core.resilience import CircuitOpenError

if TYPE_CHECKING:
    from app.ai.protocols import CompletionResponse, Message
    from app.ai.registry import ProviderRegistry

logger = get_logger(__name__)


@dataclass(frozen=True)
class FallbackEntry:
    """A single provider:model pair in a fallback chain."""

    provider: str
    model: str

    @classmethod
    def parse(cls, entry: str) -> FallbackEntry:
        """Parse 'provider:model' string. Raises ValueError on bad format."""
        if ":" not in entry:
            raise ValueError(f"Fallback entry must be 'provider:model', got: {entry!r}")
        provider, model = entry.split(":", 1)
        if not provider or not model:
            raise ValueError(f"Empty provider or model in fallback entry: {entry!r}")
        return cls(provider=provider, model=model)


@dataclass(frozen=True)
class FallbackEvent:
    """Record of a single fallback attempt."""

    tier: str
    failed_provider: str
    failed_model: str
    error_type: str
    error_message: str
    next_provider: str
    next_model: str
    elapsed_ms: float


@dataclass(frozen=True)
class FallbackChain:
    """Ordered list of provider:model entries for a tier."""

    tier: str
    entries: tuple[FallbackEntry, ...]

    @property
    def primary(self) -> FallbackEntry:
        return self.entries[0]

    @property
    def has_fallbacks(self) -> bool:
        return len(self.entries) > 1


def parse_fallback_chains(raw: dict[str, list[str]]) -> dict[str, FallbackChain]:
    """Parse config dict into FallbackChain objects.

    Args:
        raw: Mapping of tier -> list of "provider:model" strings.

    Returns:
        Mapping of tier -> FallbackChain. Tiers with <1 entry are skipped.
    """
    chains: dict[str, FallbackChain] = {}
    for tier, entries_raw in raw.items():
        if not entries_raw:
            continue
        entries = tuple(FallbackEntry.parse(e) for e in entries_raw)
        chains[tier] = FallbackChain(tier=tier, entries=entries)
        logger.info(
            "fallback.chain_loaded",
            tier=tier,
            chain=[f"{e.provider}:{e.model}" for e in entries],
        )
    return chains


# ── Retryable error detection ──

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _is_retryable(error: Exception) -> bool:
    """Check if an error should trigger fallback to next model.

    Retryable: timeout, rate limit, server errors, circuit open.
    NOT retryable: auth errors (401/403), bad request (400), not found (404).
    """
    # Circuit breaker open
    if isinstance(error, CircuitOpenError):
        return True

    # asyncio/httpx timeouts
    if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
        return True

    # httpx-specific errors
    try:
        import httpx

        if isinstance(error, httpx.TimeoutException):
            return True
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in _RETRYABLE_STATUS_CODES
    except ImportError:
        pass

    # Anthropic SDK errors
    try:
        import anthropic

        if isinstance(error, anthropic.RateLimitError):
            return True
        if isinstance(error, anthropic.InternalServerError):
            return True
        if isinstance(error, anthropic.APITimeoutError):
            return True
        if isinstance(error, anthropic.APIConnectionError):
            return True
    except ImportError:
        pass

    # OpenAI SDK errors
    try:
        import openai

        if isinstance(error, openai.RateLimitError):
            return True
        if isinstance(error, openai.InternalServerError):
            return True
        if isinstance(error, openai.APITimeoutError):
            return True
        if isinstance(error, openai.APIConnectionError):
            return True
    except ImportError:
        pass

    # Check for status_code attribute (generic HTTP errors)
    status = getattr(error, "status_code", None)
    return bool(status is not None and status in _RETRYABLE_STATUS_CODES)


# ── Core fallback caller ──


async def call_with_fallback(
    chain: FallbackChain,
    registry: ProviderRegistry,
    messages: list[Message],
    **kwargs: Any,  # noqa: ANN401
) -> CompletionResponse:
    """Try each model in the chain until one succeeds.

    Args:
        chain: Ordered fallback chain for the tier.
        registry: Provider registry to resolve providers.
        messages: Chat messages to send.
        **kwargs: Additional kwargs passed to provider.complete()
            (max_tokens, temperature, etc.). model_override is set
            automatically per chain entry.

    Returns:
        CompletionResponse from the first successful model.

    Raises:
        The last error encountered if all models in the chain fail.
    """
    last_error: Exception | None = None

    for i, entry in enumerate(chain.entries):
        start = time.monotonic()
        try:
            provider = registry.get_llm(entry.provider)
            result = await provider.complete(messages, model_override=entry.model, **kwargs)
            if i > 0:
                logger.info(
                    "fallback.succeeded",
                    tier=chain.tier,
                    provider=entry.provider,
                    model=entry.model,
                    attempt=i + 1,
                )
            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            last_error = e

            # Check if we should try the next model
            if not _is_retryable(e):
                logger.warning(
                    "fallback.non_retryable_error",
                    tier=chain.tier,
                    provider=entry.provider,
                    model=entry.model,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                raise  # Non-retryable — don't try fallbacks

            # Log the fallback event
            next_entry = chain.entries[i + 1] if i + 1 < len(chain.entries) else None
            if next_entry is not None:
                event = FallbackEvent(
                    tier=chain.tier,
                    failed_provider=entry.provider,
                    failed_model=entry.model,
                    error_type=type(e).__name__,
                    error_message=str(e)[:200],
                    next_provider=next_entry.provider,
                    next_model=next_entry.model,
                    elapsed_ms=round(elapsed_ms, 1),
                )
                logger.warning(
                    "fallback.cascading",
                    tier=event.tier,
                    failed_provider=event.failed_provider,
                    failed_model=event.failed_model,
                    error_type=event.error_type,
                    next_provider=event.next_provider,
                    next_model=event.next_model,
                    elapsed_ms=event.elapsed_ms,
                )
            else:
                logger.error(
                    "fallback.chain_exhausted",
                    tier=chain.tier,
                    failed_provider=entry.provider,
                    failed_model=entry.model,
                    error_type=type(e).__name__,
                    total_attempts=len(chain.entries),
                )

    # All entries exhausted — at least one entry always exists
    if last_error is None:  # pragma: no cover
        raise RuntimeError("Fallback chain had no entries")
    raise last_error
