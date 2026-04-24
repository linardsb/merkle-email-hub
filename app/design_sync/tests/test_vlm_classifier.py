"""Tests for VLM-assisted section classification fallback."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.protocols import CompletionResponse
from app.design_sync.vlm_classifier import (
    _CACHE_MAX_SIZE,
    _vlm_cache,
    clear_vlm_cache,
    vlm_classify_section,
)

_CANDIDATE_TYPES = [
    "hero-block",
    "text-block",
    "product-grid",
    "article-card",
    "image-gallery",
    "navigation-bar",
    "category-nav",
]
_FAKE_SCREENSHOT = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_vlm_cache()


def _mock_settings(*, enabled: bool = True) -> Any:
    """Patch get_settings with vlm_fallback_enabled."""
    mock_ds = type(
        "DS",
        (),
        {
            "vlm_fallback_enabled": enabled,
            "low_match_confidence_threshold": 0.6,
        },
    )()
    mock_s = type("S", (), {"design_sync": mock_ds})()
    return patch("app.design_sync.vlm_classifier.get_settings", return_value=mock_s)


def _make_provider(content: str, *, side_effect: Exception | None = None) -> AsyncMock:
    provider = AsyncMock()
    if side_effect:
        provider.complete.side_effect = side_effect
    else:
        provider.complete.return_value = CompletionResponse(
            content=content,
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
    return provider


class TestVLMClassifySection:
    @pytest.mark.asyncio
    async def test_vlm_disabled_returns_none(self) -> None:
        """VLM fallback disabled -> returns None, no LLM call."""
        provider = _make_provider('{"component_type": "hero-block", "confidence": 0.9}')
        with (
            _mock_settings(enabled=False),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await vlm_classify_section(_FAKE_SCREENSHOT, _CANDIDATE_TYPES)

        assert result is None
        provider.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_vlm_classify_success(self) -> None:
        """Valid VLM response -> VLMClassificationResult with correct type + confidence."""
        provider = _make_provider('{"component_type": "product-grid", "confidence": 0.85}')
        with (
            _mock_settings(enabled=True),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await vlm_classify_section(_FAKE_SCREENSHOT, _CANDIDATE_TYPES)

        assert result is not None
        assert result.component_type == "product-grid"
        assert result.confidence == 0.85
        assert result.source == "vlm_fallback"
        assert provider.complete.call_count == 1

    @pytest.mark.asyncio
    async def test_vlm_low_confidence_returns_none(self) -> None:
        """VLM returns confidence < 0.5 -> returns None."""
        provider = _make_provider('{"component_type": "product-grid", "confidence": 0.3}')
        with (
            _mock_settings(enabled=True),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await vlm_classify_section(_FAKE_SCREENSHOT, _CANDIDATE_TYPES)

        assert result is None

    @pytest.mark.asyncio
    async def test_vlm_invalid_type_returns_none(self) -> None:
        """VLM returns type not in candidate_types -> returns None."""
        provider = _make_provider('{"component_type": "banana-section", "confidence": 0.9}')
        with (
            _mock_settings(enabled=True),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await vlm_classify_section(_FAKE_SCREENSHOT, _CANDIDATE_TYPES)

        assert result is None

    @pytest.mark.asyncio
    async def test_vlm_api_error_returns_none(self) -> None:
        """provider.complete raises -> returns None (graceful fallback)."""
        provider = _make_provider("", side_effect=RuntimeError("API down"))
        with (
            _mock_settings(enabled=True),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await vlm_classify_section(_FAKE_SCREENSHOT, _CANDIDATE_TYPES)

        assert result is None

    @pytest.mark.asyncio
    async def test_vlm_cache_hit(self) -> None:
        """Second call with same screenshot -> cache hit, provider called once."""
        provider = _make_provider('{"component_type": "article-card", "confidence": 0.8}')
        with (
            _mock_settings(enabled=True),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            # First call — cache miss
            result1 = await vlm_classify_section(_FAKE_SCREENSHOT, _CANDIDATE_TYPES)
            # Second call — cache hit
            result2 = await vlm_classify_section(_FAKE_SCREENSHOT, _CANDIDATE_TYPES)

        assert result1 is not None
        assert result2 is not None
        assert result1.component_type == "article-card"
        assert result2.component_type == "article-card"
        assert provider.complete.call_count == 1

    @pytest.mark.asyncio
    async def test_vlm_cache_eviction(self) -> None:
        """Cache exceeds _CACHE_MAX_SIZE -> cleared, re-calls provider."""
        provider = _make_provider('{"component_type": "hero-block", "confidence": 0.9}')

        # Pre-fill cache to capacity
        for i in range(_CACHE_MAX_SIZE):
            _vlm_cache[f"fake_hash_{i}"] = ("text-block", 0.5)
        assert len(_vlm_cache) == _CACHE_MAX_SIZE

        with (
            _mock_settings(enabled=True),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await vlm_classify_section(_FAKE_SCREENSHOT, _CANDIDATE_TYPES)

        assert result is not None
        assert result.component_type == "hero-block"
        # Cache was cleared and re-populated with just the new entry
        assert len(_vlm_cache) == 1


class TestMatchSectionWithVLMFallback:
    @pytest.mark.asyncio
    async def test_low_confidence_triggers_vlm(self) -> None:
        """Integration: low-confidence heuristic match + VLM -> new ComponentMatch."""
        from app.design_sync.component_matcher import match_section_with_vlm_fallback
        from app.design_sync.figma.layout_analyzer import (
            EmailSection,
            EmailSectionType,
        )

        # Section that produces low confidence (no candidates -> 0.5)
        section = EmailSection(
            section_type=EmailSectionType.CONTENT,
            node_id="n1",
            node_name="Ambiguous",
            width=600,
            height=300,
        )

        provider = _make_provider('{"component_type": "product-grid", "confidence": 0.85}')

        mock_ds = type(
            "DS",
            (),
            {
                "vlm_fallback_enabled": True,
                "low_match_confidence_threshold": 0.6,
            },
        )()
        mock_s = type("S", (), {"design_sync": mock_ds})()

        with (
            patch(
                "app.design_sync.vlm_classifier.get_settings",
                return_value=mock_s,
            ),
            patch(
                "app.core.config.get_settings",
                return_value=mock_s,
            ),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await match_section_with_vlm_fallback(
                section,
                0,
                screenshot=_FAKE_SCREENSHOT,
                candidate_types=_CANDIDATE_TYPES,
            )

        assert result.component_slug == "product-grid"
        assert result.confidence == 0.85
