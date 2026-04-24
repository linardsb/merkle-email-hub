"""Tests for the iterative verification loop orchestrator (Phase 47.4)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.design_sync.correction_applicator import CorrectionResult
from app.design_sync.figma.layout_analyzer import EmailSection, EmailSectionType
from app.design_sync.visual_verify import (
    SectionCorrection,
    VerificationLoopResult,
    VerificationResult,
    run_verification_loop,
)

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_section(node_id: str = "n1") -> EmailSection:
    return EmailSection(
        section_type=EmailSectionType.HERO,
        node_id=node_id,
        node_name="Hero",
        y_position=0,
        height=200,
    )


def _make_correction(
    node_id: str = "n1",
    section_idx: int = 0,
    confidence: float = 0.9,
) -> SectionCorrection:
    return SectionCorrection(
        node_id=node_id,
        section_idx=section_idx,
        correction_type="color",
        css_selector="h1",
        css_property="color",
        current_value="#333",
        correct_value="#2D2D2D",
        confidence=confidence,
        reasoning="heading color mismatch",
    )


def _make_verification_result(
    iteration: int,
    fidelity: float,
    corrections_count: int = 0,
    *,
    converged: bool = False,
) -> VerificationResult:
    corrections = [_make_correction() for _ in range(corrections_count)]
    return VerificationResult(
        iteration=iteration,
        fidelity_score=fidelity,
        section_scores={"n1": (1.0 - fidelity) * 100},
        corrections=corrections,
        pixel_diff_pct=(1.0 - fidelity) * 100,
        converged=converged,
    )


def _mock_settings(
    *,
    enabled: bool = True,
    max_iterations: int = 3,
    target_fidelity: float = 0.97,
    confidence_threshold: float = 0.7,
) -> MagicMock:
    mock_ds = MagicMock()
    mock_ds.vlm_verify_enabled = enabled
    mock_ds.vlm_verify_max_iterations = max_iterations
    mock_ds.vlm_verify_target_fidelity = target_fidelity
    mock_ds.vlm_verify_confidence_threshold = confidence_threshold
    mock_ds.vlm_verify_model = ""
    mock_ds.vlm_verify_timeout = 5.0
    mock_ds.vlm_verify_diff_skip_threshold = 2.0
    mock_ds.vlm_verify_max_sections = 20
    mock_s = MagicMock()
    mock_s.design_sync = mock_ds
    return mock_s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVerificationLoop:
    @pytest.mark.asyncio
    async def test_loop_converges_3_iterations(self) -> None:
        """3 iterations: 0.82->0.91->0.96->0.98, converges when fidelity exceeds target."""
        results = [
            _make_verification_result(0, 0.82, corrections_count=3),
            _make_verification_result(1, 0.91, corrections_count=2),
            _make_verification_result(2, 0.98, corrections_count=0, converged=True),
        ]
        correction_results = [
            CorrectionResult(html="<html>v2</html>", applied=[_make_correction()] * 3),
            CorrectionResult(html="<html>v3</html>", applied=[_make_correction()] * 2),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.design_sync.correction_applicator.apply_corrections",
                side_effect=correction_results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert isinstance(result, VerificationLoopResult)
        assert len(result.iterations) == 3
        assert result.initial_fidelity == pytest.approx(0.82)  # pyright: ignore[reportUnknownMemberType]
        assert result.final_fidelity == pytest.approx(0.98)  # pyright: ignore[reportUnknownMemberType]
        assert result.converged is True
        assert result.reverted is False
        assert result.total_corrections_applied == 5

    @pytest.mark.asyncio
    async def test_loop_regression_reverts(self) -> None:
        """Score drops in iteration 2 -> reverts to iteration 1 HTML, reverted=True."""
        results = [
            _make_verification_result(0, 0.85, corrections_count=2),
            _make_verification_result(1, 0.80, corrections_count=1),  # Regression
        ]
        correction_results = [
            CorrectionResult(html="<html>v2</html>", applied=[_make_correction()] * 2),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.design_sync.correction_applicator.apply_corrections",
                side_effect=correction_results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert result.reverted is True
        assert len(result.iterations) == 2
        assert result.final_html == "<html>v1</html>"  # Reverted to pre-correction HTML

    @pytest.mark.asyncio
    async def test_loop_max_iterations_cap(self) -> None:
        """Reaches max_iterations=2 -> stops, returns best result."""
        results = [
            _make_verification_result(0, 0.80, corrections_count=2),
            _make_verification_result(1, 0.85, corrections_count=2),
        ]
        correction_results = [
            CorrectionResult(html="<html>v2</html>", applied=[_make_correction()] * 2),
            CorrectionResult(html="<html>v3</html>", applied=[_make_correction()] * 2),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.design_sync.correction_applicator.apply_corrections",
                side_effect=correction_results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
                max_iterations=2,
            )

        assert len(result.iterations) == 2
        assert result.converged is False
        assert result.total_corrections_applied == 4

    @pytest.mark.asyncio
    async def test_loop_immediate_convergence(self) -> None:
        """First iteration has no corrections -> converged=True, 1 iteration."""
        results = [
            _make_verification_result(0, 0.99, corrections_count=0, converged=True),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>perfect</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert len(result.iterations) == 1
        assert result.converged is True
        assert result.total_corrections_applied == 0
        assert result.final_html == "<html>perfect</html>"

    @pytest.mark.asyncio
    async def test_loop_disabled_returns_empty(self) -> None:
        """vlm_verify_enabled=False -> single-iteration empty result."""
        with patch(
            "app.design_sync.visual_verify.get_settings",
            return_value=_mock_settings(enabled=False),
        ):
            result = await run_verification_loop(
                "<html>test</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert result.iterations == []
        assert result.converged is False
        assert result.final_html == "<html>test</html>"
        assert result.total_corrections_applied == 0

    @pytest.mark.asyncio
    async def test_loop_rendering_failure_graceful(self) -> None:
        """render_screenshots raises -> returns result from prior iterations."""
        render_mock = AsyncMock()
        render_mock.side_effect = [
            [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}],
            RuntimeError("render failed"),
        ]
        results = [
            _make_verification_result(0, 0.85, corrections_count=2),
        ]
        correction_results = [
            CorrectionResult(html="<html>v2</html>", applied=[_make_correction()] * 2),
        ]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.design_sync.correction_applicator.apply_corrections",
                side_effect=correction_results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                render_mock,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert len(result.iterations) == 1
        assert result.initial_fidelity == pytest.approx(0.85)  # pyright: ignore[reportUnknownMemberType]
        assert result.final_html == "<html>v2</html>"

    @pytest.mark.asyncio
    async def test_loop_accumulates_corrections(self) -> None:
        """Total corrections = sum of applied across iterations."""
        results = [
            _make_verification_result(0, 0.80, corrections_count=3),
            _make_verification_result(1, 0.90, corrections_count=2),
            _make_verification_result(2, 0.98, corrections_count=0, converged=True),
        ]
        correction_results = [
            CorrectionResult(
                html="<html>v2</html>",
                applied=[_make_correction()] * 3,
            ),
            CorrectionResult(
                html="<html>v3</html>",
                applied=[_make_correction()] * 2,
            ),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.design_sync.correction_applicator.apply_corrections",
                side_effect=correction_results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert result.total_corrections_applied == 5
        assert len(result.iterations) == 3

    @pytest.mark.asyncio
    async def test_loop_confidence_threshold_applied(self) -> None:
        """Low-confidence corrections skipped via threshold from config."""
        low_conf_correction = _make_correction(confidence=0.3)
        high_conf_correction = _make_correction(confidence=0.9)
        results = [
            VerificationResult(
                iteration=0,
                fidelity_score=0.85,
                section_scores={"n1": 15.0},
                corrections=[low_conf_correction, high_conf_correction],
                pixel_diff_pct=15.0,
                converged=False,
            ),
            _make_verification_result(1, 0.98, corrections_count=0, converged=True),
        ]
        # apply_corrections receives both but only applies the high-confidence one
        correction_results = [
            CorrectionResult(
                html="<html>v2</html>",
                applied=[high_conf_correction],
                skipped=[low_conf_correction],
            ),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(confidence_threshold=0.7),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.design_sync.correction_applicator.apply_corrections",
                side_effect=correction_results,
            ) as mock_apply,
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        # Verify confidence_threshold was passed to apply_corrections
        mock_apply.assert_called_once()
        call_kwargs = mock_apply.call_args
        assert call_kwargs[1]["confidence_threshold"] == pytest.approx(0.7)  # pyright: ignore[reportUnknownMemberType]
        assert result.total_corrections_applied == 1

    @pytest.mark.asyncio
    async def test_loop_compare_exception_breaks(self) -> None:
        """compare_sections raises -> loop breaks, returns partial result."""
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=RuntimeError("VLM crashed"),
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert result.iterations == []
        assert result.final_html == "<html>v1</html>"
        assert result.converged is False

    @pytest.mark.asyncio
    async def test_loop_apply_exception_breaks(self) -> None:
        """apply_corrections raises -> loop breaks, returns partial result."""
        results = [
            _make_verification_result(0, 0.80, corrections_count=2),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.design_sync.correction_applicator.apply_corrections",
                side_effect=RuntimeError("lxml parse error"),
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert len(result.iterations) == 1
        assert result.final_html == "<html>v1</html>"
        assert result.total_corrections_applied == 0

    @pytest.mark.asyncio
    async def test_loop_crop_failure_continues(self) -> None:
        """One section crop fails -> section skipped, loop continues."""
        s1 = _make_section("n1")
        s2 = _make_section("n2")

        crop_side_effects = [_FAKE_PNG, RuntimeError("bad image")]

        results = [
            _make_verification_result(0, 0.99, corrections_count=0, converged=True),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                side_effect=crop_side_effects,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG, "n2": _FAKE_PNG},
                [s1, s2],
            )

        assert len(result.iterations) == 1
        assert result.converged is True

    @pytest.mark.asyncio
    async def test_loop_no_render_result(self) -> None:
        """render_screenshots returns [] -> loop breaks immediately."""
        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert result.iterations == []
        assert result.final_html == "<html>v1</html>"
        assert result.converged is False

    @pytest.mark.asyncio
    async def test_loop_fidelity_at_exact_target(self) -> None:
        """fidelity == target (0.97) -> converged (boundary condition)."""
        results = [
            _make_verification_result(0, 0.97, corrections_count=0),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(target_fidelity=0.97),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert len(result.iterations) == 1
        assert result.converged is True

    @pytest.mark.asyncio
    async def test_loop_zero_sections(self) -> None:
        """Empty sections list -> single iteration, immediate convergence."""
        results = [
            VerificationResult(
                iteration=0,
                fidelity_score=1.0,
                section_scores={},
                corrections=[],
                pixel_diff_pct=0.0,
                converged=True,
            ),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {},
                [],
            )

        assert len(result.iterations) == 1
        assert result.converged is True
        assert result.total_corrections_applied == 0

    @pytest.mark.asyncio
    async def test_loop_vlm_cost_tokens_tracking(self) -> None:
        """Verify total_vlm_cost_tokens field is present on result (currently 0)."""
        results = [
            _make_verification_result(0, 0.99, corrections_count=0, converged=True),
        ]
        render_result = [{"client_name": "gmail_web", "image_bytes": _FAKE_PNG}]

        with (
            patch(
                "app.design_sync.visual_verify.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.design_sync.visual_verify.compare_sections",
                new_callable=AsyncMock,
                side_effect=results,
            ),
            patch(
                "app.rendering.local.service.LocalRenderingProvider.render_screenshots",
                new_callable=AsyncMock,
                return_value=render_result,
            ),
            patch(
                "app.rendering.screenshot_crop.crop_section",
                return_value=_FAKE_PNG,
            ),
        ):
            result = await run_verification_loop(
                "<html>v1</html>",
                {"n1": _FAKE_PNG},
                [_make_section("n1")],
            )

        assert hasattr(result, "total_vlm_cost_tokens")
        assert isinstance(result.total_vlm_cost_tokens, int)
        assert result.total_vlm_cost_tokens >= 0
