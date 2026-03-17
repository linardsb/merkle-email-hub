"""Integration tests for fallback chain routing (Phase 22.4)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from app.ai.routing import get_fallback_chain, reset_fallback_chains


@pytest.fixture(autouse=True)
def _reset_cache() -> Generator[None, None, None]:
    """Reset fallback chain cache before each test."""
    reset_fallback_chains()
    yield
    reset_fallback_chains()


def test_get_fallback_chain_no_config() -> None:
    with patch("app.ai.routing.get_settings") as mock_settings:
        mock_settings.return_value.ai.fallback_chains = {}
        result = get_fallback_chain("complex")
        assert result is None


def test_get_fallback_chain_configured_tier() -> None:
    with patch("app.ai.routing.get_settings") as mock_settings:
        mock_settings.return_value.ai.fallback_chains = {
            "complex": ["anthropic:claude-opus-4-6", "openai:gpt-4o"],
        }
        chain = get_fallback_chain("complex")
        assert chain is not None
        assert chain.tier == "complex"
        assert len(chain.entries) == 2
        assert chain.entries[0].provider == "anthropic"
        assert chain.entries[1].provider == "openai"


def test_get_fallback_chain_unconfigured_tier() -> None:
    with patch("app.ai.routing.get_settings") as mock_settings:
        mock_settings.return_value.ai.fallback_chains = {
            "complex": ["anthropic:claude-opus-4-6", "openai:gpt-4o"],
        }
        result = get_fallback_chain("standard")
        assert result is None


def test_reset_fallback_chains() -> None:
    with patch("app.ai.routing.get_settings") as mock_settings:
        mock_settings.return_value.ai.fallback_chains = {
            "complex": ["anthropic:claude-opus-4-6"],
        }
        # Load cache
        get_fallback_chain("complex")

        # Reset and change config
        reset_fallback_chains()
        mock_settings.return_value.ai.fallback_chains = {
            "complex": ["openai:gpt-4o"],
        }

        chain = get_fallback_chain("complex")
        assert chain is not None
        assert chain.entries[0].provider == "openai"


def test_fallback_chains_config_parsing() -> None:
    with patch("app.ai.routing.get_settings") as mock_settings:
        mock_settings.return_value.ai.fallback_chains = {
            "complex": ["anthropic:claude-opus-4-6", "openai:gpt-4o"],
            "standard": ["anthropic:claude-sonnet-4-6", "openai:gpt-4o-mini"],
            "lightweight": ["openai:gpt-4o-mini"],
        }

        complex_chain = get_fallback_chain("complex")
        standard_chain = get_fallback_chain("standard")
        lightweight_chain = get_fallback_chain("lightweight")

        assert complex_chain is not None
        assert complex_chain.has_fallbacks is True
        assert standard_chain is not None
        assert standard_chain.has_fallbacks is True
        assert lightweight_chain is not None
        assert lightweight_chain.has_fallbacks is False


def test_get_fallback_chain_caches() -> None:
    with patch("app.ai.routing.get_settings") as mock_settings:
        mock_settings.return_value.ai.fallback_chains = {
            "complex": ["anthropic:claude-opus-4-6", "openai:gpt-4o"],
        }

        chain1 = get_fallback_chain("complex")
        chain2 = get_fallback_chain("complex")

        # Same object — cache hit
        assert chain1 is chain2
        # Settings only called once for parsing
        assert mock_settings.call_count == 1
