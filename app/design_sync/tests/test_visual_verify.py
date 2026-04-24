"""Tests for VLM visual comparison service (Phase 47.2)."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.protocols import CompletionResponse
from app.design_sync.figma.layout_analyzer import EmailSection, EmailSectionType
from app.design_sync.visual_verify import (
    SectionCorrection,
    VerificationResult,
    _parse_vlm_response,
    clear_verify_cache,
    compare_sections,
)
from app.rendering.visual_diff import DiffResult

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

_VLM_JSON_3_CORRECTIONS = (
    '[{"correction_type":"color","css_selector":"h1","css_property":"color",'
    '"current_value":"#333","correct_value":"#2D2D2D","confidence":0.9,'
    '"reasoning":"heading color mismatch"},'
    '{"correction_type":"spacing","css_selector":".hero","css_property":"padding-top",'
    '"current_value":"16px","correct_value":"24px","confidence":0.85,'
    '"reasoning":"padding too small"},'
    '{"correction_type":"font","css_selector":"p","css_property":"font-size",'
    '"current_value":"14px","correct_value":"16px","confidence":0.8,'
    '"reasoning":"body text size off"}]'
)


@pytest.fixture(autouse=True)
def _clear_cache() -> Generator[None, None, None]:
    clear_verify_cache()
    yield
    clear_verify_cache()


def _make_section(node_id: str = "123") -> EmailSection:
    return EmailSection(
        section_type=EmailSectionType.HERO,
        node_id=node_id,
        node_name="Hero Section",
    )


def _mock_settings(*, enabled: bool = True, diff_threshold: float = 2.0) -> Any:
    mock_ds = type(
        "DS",
        (),
        {
            "vlm_verify_enabled": enabled,
            "vlm_verify_model": "",
            "vlm_verify_timeout": 5.0,
            "vlm_verify_diff_skip_threshold": diff_threshold,
            "vlm_verify_max_sections": 20,
        },
    )()
    mock_s = type("S", (), {"design_sync": mock_ds})()
    return patch("app.design_sync.visual_verify.get_settings", return_value=mock_s)


def _mock_odiff(diff_pct: float = 5.0) -> Any:
    result = DiffResult(
        identical=diff_pct == 0.0,
        diff_percentage=diff_pct,
        diff_image=None,
        pixel_count=int(diff_pct * 100),
        changed_regions=[],
    )
    return patch(
        "app.rendering.visual_diff.run_odiff",
        new_callable=AsyncMock,
        return_value=result,
    )


def _make_provider(content: str) -> AsyncMock:
    provider = AsyncMock()
    provider.complete.return_value = CompletionResponse(
        content=content,
        model="test",
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
    )
    return provider


class TestCompareSections:
    @pytest.mark.asyncio
    async def test_disabled_returns_unconverged(self) -> None:
        """vlm_verify_enabled=False -> unconverged result, no calls."""
        with _mock_settings(enabled=False):
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        assert isinstance(result, VerificationResult)
        assert result.converged is False
        assert result.corrections == []
        assert result.section_scores == {}

    @pytest.mark.asyncio
    async def test_odiff_prefilter_skips_low_diff(self) -> None:
        """ODiff < threshold -> VLM never called."""
        provider = _make_provider(_VLM_JSON_3_CORRECTIONS)
        with (
            _mock_settings(enabled=True, diff_threshold=2.0),
            _mock_odiff(diff_pct=1.5),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        assert result.corrections == []
        assert result.converged is True
        assert result.section_scores["n1"] == 1.5
        provider.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_odiff_prefilter_calls_vlm_above_threshold(self) -> None:
        """ODiff > threshold -> VLM called, corrections returned."""
        provider = _make_provider(_VLM_JSON_3_CORRECTIONS)
        with (
            _mock_settings(enabled=True, diff_threshold=2.0),
            _mock_odiff(diff_pct=5.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        assert len(result.corrections) == 3
        assert result.converged is False
        provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_vlm_returns_corrections(self) -> None:
        """VLM JSON response parsed into SectionCorrection list."""
        provider = _make_provider(_VLM_JSON_3_CORRECTIONS)
        with (
            _mock_settings(enabled=True),
            _mock_odiff(diff_pct=10.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        c = result.corrections[0]
        assert isinstance(c, SectionCorrection)
        assert c.correction_type == "color"
        assert c.css_selector == "h1"
        assert c.current_value == "#333"
        assert c.correct_value == "#2D2D2D"
        assert c.confidence == 0.9

    @pytest.mark.asyncio
    async def test_empty_corrections_converged(self) -> None:
        """VLM returns [] for all sections -> converged=True."""
        provider = _make_provider("[]")
        with (
            _mock_settings(enabled=True),
            _mock_odiff(diff_pct=5.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        assert result.corrections == []
        assert result.converged is True

    @pytest.mark.asyncio
    async def test_vlm_timeout_graceful(self) -> None:
        """VLM timeout -> empty corrections, no crash."""
        provider = AsyncMock()
        provider.complete.side_effect = TimeoutError("timed out")
        with (
            _mock_settings(enabled=True),
            _mock_odiff(diff_pct=5.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        assert result.corrections == []
        assert result.converged is True  # No corrections = converged

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        """Same bytes twice -> VLM called once, second uses cache."""
        provider = _make_provider(_VLM_JSON_3_CORRECTIONS)
        with (
            _mock_settings(enabled=True),
            _mock_odiff(diff_pct=5.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            # First call
            await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
            # Second call — should use cache
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        assert len(result.corrections) == 3
        # VLM called only once (first time), cached on second
        assert provider.complete.call_count == 1


class TestMultiSectionComparison:
    @pytest.mark.asyncio
    async def test_multi_section_mixed_results(self) -> None:
        """2 sections: one below ODiff threshold (skipped), one above (VLM called)."""
        provider = _make_provider(_VLM_JSON_3_CORRECTIONS)
        # ODiff returns 1.0 for first call (below threshold), 5.0 for second
        odiff_results = [
            DiffResult(
                identical=False,
                diff_percentage=1.0,
                diff_image=None,
                pixel_count=100,
                changed_regions=[],
            ),
            DiffResult(
                identical=False,
                diff_percentage=5.0,
                diff_image=None,
                pixel_count=500,
                changed_regions=[],
            ),
        ]
        with (
            _mock_settings(enabled=True, diff_threshold=2.0),
            patch(
                "app.rendering.visual_diff.run_odiff",
                new_callable=AsyncMock,
                side_effect=odiff_results,
            ),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG, "n2": _FAKE_PNG},
                {"n1": _FAKE_PNG, "n2": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1"), _make_section("n2")],
            )
        # n1 below threshold (no VLM), n2 above (VLM called -> 3 corrections)
        assert len(result.corrections) == 3
        assert result.section_scores["n1"] == 1.0
        assert result.section_scores["n2"] == 5.0
        provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_sections_cap(self) -> None:
        """vlm_verify_max_sections=1 with 3 sections -> only 1 processed."""
        mock_ds = type(
            "DS",
            (),
            {
                "vlm_verify_enabled": True,
                "vlm_verify_model": "",
                "vlm_verify_timeout": 5.0,
                "vlm_verify_diff_skip_threshold": 2.0,
                "vlm_verify_max_sections": 1,
            },
        )()
        mock_s = type("S", (), {"design_sync": mock_ds})()
        provider = _make_provider("[]")
        with (
            patch("app.design_sync.visual_verify.get_settings", return_value=mock_s),
            _mock_odiff(diff_pct=5.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG, "n2": _FAKE_PNG, "n3": _FAKE_PNG},
                {"n1": _FAKE_PNG, "n2": _FAKE_PNG, "n3": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1"), _make_section("n2"), _make_section("n3")],
            )
        # Only 1 section processed
        assert len(result.section_scores) == 1

    @pytest.mark.asyncio
    async def test_missing_rendered_screenshot(self) -> None:
        """Design has node n1, rendered doesn't -> node skipped, no crash."""
        with (
            _mock_settings(enabled=True),
            _mock_odiff(diff_pct=5.0),
        ):
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n2": _FAKE_PNG},  # different node_id
                "<html></html>",
                [_make_section("n1")],
            )
        assert result.section_scores == {}
        assert result.corrections == []
        assert result.converged is True


class TestFidelityCalculation:
    @pytest.mark.asyncio
    async def test_fidelity_score_math(self) -> None:
        """Verify fidelity = 1.0 - avg_diff/100 with known values."""
        # Two sections: diff 10.0 and 30.0 -> avg = 20.0 -> fidelity = 0.80
        odiff_results = [
            DiffResult(
                identical=False,
                diff_percentage=10.0,
                diff_image=None,
                pixel_count=1000,
                changed_regions=[],
            ),
            DiffResult(
                identical=False,
                diff_percentage=30.0,
                diff_image=None,
                pixel_count=3000,
                changed_regions=[],
            ),
        ]
        provider = _make_provider("[]")
        with (
            _mock_settings(enabled=True, diff_threshold=50.0),
            patch(
                "app.rendering.visual_diff.run_odiff",
                new_callable=AsyncMock,
                side_effect=odiff_results,
            ),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG, "n2": _FAKE_PNG},
                {"n1": _FAKE_PNG, "n2": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1"), _make_section("n2")],
            )
        assert result.fidelity_score == pytest.approx(0.80)  # pyright: ignore[reportUnknownMemberType]
        assert result.pixel_diff_pct == pytest.approx(20.0)  # pyright: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_cache_eviction(self) -> None:
        """Fill 256 entries -> cache cleared, next call re-populates."""
        from app.design_sync.visual_verify import _CACHE_MAX_SIZE, _vlm_cache

        # Pre-fill cache to max
        for i in range(_CACHE_MAX_SIZE):
            _vlm_cache[f"key_{i}"] = []

        assert len(_vlm_cache) == _CACHE_MAX_SIZE

        provider = _make_provider("[]")
        with (
            _mock_settings(enabled=True),
            _mock_odiff(diff_pct=5.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )

        # Cache was cleared and re-populated with 1 new entry
        assert len(_vlm_cache) == 1


class TestVLMErrorHandling:
    @pytest.mark.asyncio
    async def test_vlm_generic_exception(self) -> None:
        """Provider raises RuntimeError (not timeout) -> graceful empty."""
        provider = AsyncMock()
        provider.complete.side_effect = RuntimeError("model overloaded")
        with (
            _mock_settings(enabled=True),
            _mock_odiff(diff_pct=5.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        assert result.corrections == []
        assert result.converged is True

    @pytest.mark.asyncio
    async def test_odiff_error_returns_max_diff(self) -> None:
        """_run_odiff_for_section raises -> returns 100.0 (VLM still called)."""
        provider = _make_provider("[]")
        with (
            _mock_settings(enabled=True),
            patch(
                "app.rendering.visual_diff.run_odiff",
                new_callable=AsyncMock,
                side_effect=RuntimeError("odiff binary missing"),
            ),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            result = await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
            )
        # ODiff error -> 100.0 diff -> VLM called
        assert result.section_scores["n1"] == 100.0
        provider.complete.assert_called_once()


class TestParseVLMResponse:
    def test_parse_invalid_json(self) -> None:
        """Invalid JSON -> empty corrections, no crash."""
        result = _parse_vlm_response("not json at all", "n1", 0)
        assert result == []

    def test_parse_markdown_fenced_json(self) -> None:
        """JSON wrapped in markdown code fences -> still parsed."""
        fenced = f"```json\n{_VLM_JSON_3_CORRECTIONS}\n```"
        result = _parse_vlm_response(fenced, "n1", 0)
        assert len(result) == 3

    def test_parse_invalid_correction_type(self) -> None:
        """Unknown correction_type -> item skipped."""
        result = _parse_vlm_response(
            '[{"correction_type":"banana","css_selector":"h1",'
            '"css_property":"color","current_value":"#333",'
            '"correct_value":"#2D2D2D","confidence":0.9,"reasoning":"test"}]',
            "n1",
            0,
        )
        assert result == []

    def test_parse_single_object_not_array(self) -> None:
        """VLM returns {...} instead of [{...}] -> empty list."""
        result = _parse_vlm_response(
            '{"correction_type":"color","css_selector":"h1",'
            '"css_property":"color","current_value":"#333",'
            '"correct_value":"#2D2D2D","confidence":0.9,"reasoning":"test"}',
            "n1",
            0,
        )
        assert result == []

    def test_parse_missing_fields(self) -> None:
        """VLM returns partial object -> still parses with defaults."""
        result = _parse_vlm_response(
            '[{"correction_type":"color"}]',
            "n1",
            0,
        )
        assert len(result) == 1
        c = result[0]
        assert c.correction_type == "color"
        assert c.css_selector == ""
        assert c.css_property == ""
        assert c.confidence == 0.5  # default
