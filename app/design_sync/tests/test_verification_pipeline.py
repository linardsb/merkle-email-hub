"""Tests for VLM verification loop pipeline integration (Phase 47.5)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.design_sync.converter_service import ConversionResult, DesignConverterService
from app.design_sync.figma.layout_analyzer import EmailSection, EmailSectionType
from app.design_sync.visual_verify import VerificationLoopResult, VerificationResult

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


def _make_result(html: str = "<html>original</html>") -> ConversionResult:
    return ConversionResult(
        html=html,
        sections_count=2,
        warnings=["token mismatch"],
        images=[{"src": "img.png"}],
        match_confidences={0: 0.85, 1: 0.91},
        figma_url="https://figma.com/file/abc",
        node_id="root",
        design_tokens_used={"bg": "#fff"},
    )


def _make_loop_result(
    final_html: str = "<html>corrected</html>",
    iterations_count: int = 2,
    initial_fidelity: float = 0.82,
    final_fidelity: float = 0.98,
) -> VerificationLoopResult:
    iterations = [
        VerificationResult(
            iteration=i,
            fidelity_score=initial_fidelity + i * 0.08,
            section_scores={"n1": 5.0 - i * 2},
            corrections=[],
            pixel_diff_pct=5.0 - i * 2,
            converged=i == iterations_count - 1,
        )
        for i in range(iterations_count)
    ]
    return VerificationLoopResult(
        iterations=iterations,
        final_html=final_html,
        initial_fidelity=initial_fidelity,
        final_fidelity=final_fidelity,
        total_corrections_applied=3,
        total_vlm_cost_tokens=1200,
        converged=True,
        reverted=False,
    )


def _mock_settings(*, enabled: bool = True, client: str = "gmail_web") -> MagicMock:
    mock_ds = MagicMock()
    mock_ds.vlm_verify_enabled = enabled
    mock_ds.vlm_verify_max_iterations = 3
    mock_ds.vlm_verify_client = client
    mock_s = MagicMock()
    mock_s.design_sync = mock_ds
    return mock_s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApplyVerification:
    """Tests for DesignConverterService._apply_verification()."""

    @pytest.mark.asyncio
    async def test_verification_disabled_skips(self) -> None:
        """vlm_verify_enabled=False → result unchanged, zero VLM calls."""
        svc = DesignConverterService()
        original = _make_result()
        screenshots = {"n1": _FAKE_PNG}
        sections = [_make_section()]

        with patch(
            "app.design_sync.converter_service.get_settings",
            return_value=_mock_settings(enabled=False),
        ):
            result = await svc._apply_verification(original, screenshots, sections, 680)

        assert result is original
        assert result.verification_iterations == 0

    @pytest.mark.asyncio
    async def test_verification_no_screenshots_skips(self) -> None:
        """Enabled but empty design_screenshots → result unchanged."""
        svc = DesignConverterService()
        original = _make_result()
        sections = [_make_section()]

        with patch(
            "app.design_sync.converter_service.get_settings",
            return_value=_mock_settings(enabled=True),
        ):
            result = await svc._apply_verification(original, {}, sections, 680)

        assert result is original

    @pytest.mark.asyncio
    async def test_verification_enabled_applies(self) -> None:
        """Enabled + screenshots → ConversionResult has verification metadata."""
        svc = DesignConverterService()
        original = _make_result()
        screenshots = {"n1": _FAKE_PNG}
        sections = [_make_section()]
        loop_result = _make_loop_result()

        with (
            patch(
                "app.design_sync.converter_service.get_settings",
                return_value=_mock_settings(enabled=True),
            ),
            patch(
                "app.design_sync.visual_verify.run_verification_loop",
                new_callable=AsyncMock,
                return_value=loop_result,
            ) as mock_loop,
        ):
            result = await svc._apply_verification(original, screenshots, sections, 680)

        mock_loop.assert_awaited_once()
        assert result.verification_iterations == 2
        assert result.verification_initial_fidelity == 0.82
        assert result.verification_final_fidelity == 0.98

    @pytest.mark.asyncio
    async def test_verification_updates_html(self) -> None:
        """Final HTML from VerificationLoopResult replaces original."""
        svc = DesignConverterService()
        original = _make_result(html="<html>old</html>")
        screenshots = {"n1": _FAKE_PNG}
        sections = [_make_section()]
        loop_result = _make_loop_result(final_html="<html>new</html>")

        with (
            patch(
                "app.design_sync.converter_service.get_settings",
                return_value=_mock_settings(enabled=True),
            ),
            patch(
                "app.design_sync.visual_verify.run_verification_loop",
                new_callable=AsyncMock,
                return_value=loop_result,
            ),
        ):
            result = await svc._apply_verification(original, screenshots, sections, 680)

        assert result.html == "<html>new</html>"

    @pytest.mark.asyncio
    async def test_verification_preserves_other_fields(self) -> None:
        """sections_count, warnings, images, match_confidences unchanged."""
        svc = DesignConverterService()
        original = _make_result()
        screenshots = {"n1": _FAKE_PNG}
        sections = [_make_section()]
        loop_result = _make_loop_result()

        with (
            patch(
                "app.design_sync.converter_service.get_settings",
                return_value=_mock_settings(enabled=True),
            ),
            patch(
                "app.design_sync.visual_verify.run_verification_loop",
                new_callable=AsyncMock,
                return_value=loop_result,
            ),
        ):
            result = await svc._apply_verification(original, screenshots, sections, 680)

        assert result.sections_count == original.sections_count
        assert result.warnings == original.warnings
        assert result.images == original.images
        assert result.match_confidences == original.match_confidences
        assert result.figma_url == original.figma_url
        assert result.node_id == original.node_id
        assert result.design_tokens_used == original.design_tokens_used

    @pytest.mark.asyncio
    async def test_verification_exception_returns_original(self) -> None:
        """run_verification_loop raises → original result returned, warning logged."""
        svc = DesignConverterService()
        original = _make_result()
        screenshots = {"n1": _FAKE_PNG}
        sections = [_make_section()]

        with (
            patch(
                "app.design_sync.converter_service.get_settings",
                return_value=_mock_settings(enabled=True),
            ),
            patch(
                "app.design_sync.visual_verify.run_verification_loop",
                new_callable=AsyncMock,
                side_effect=RuntimeError("VLM provider down"),
            ),
            patch("app.design_sync.converter_service.logger") as mock_logger,
        ):
            result = await svc._apply_verification(original, screenshots, sections, 680)

        assert result is original
        assert result.verification_iterations == 0
        mock_logger.warning.assert_called_once_with(
            "design_sync.verification_loop_failed", exc_info=True
        )
