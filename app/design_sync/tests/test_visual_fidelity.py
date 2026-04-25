"""Tests for Phase 35.6 — AI Visual Fidelity Scoring Pipeline.

Tests cover:
- SSIM scoring engine (score_fidelity, classify_severity)
- FidelityService orchestration (mocked Figma + Playwright)
- Pipeline integration (run_conversion with score_fidelity=True)
- API endpoints (auth, project access, fidelity retrieval)
"""

from __future__ import annotations

import io
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from app.design_sync.figma.layout_analyzer import (
    ColumnLayout,
    DesignLayoutDescription,
    EmailSection,
    EmailSectionType,
)
from app.design_sync.visual_scorer import (
    FidelityScore,
    SectionScore,
    _compute_design_height,
    classify_severity,
    score_fidelity,
)
from app.shared.imaging import safe_image_open

# ── Helpers ──


def _make_png(width: int, height: int, color: int = 255) -> bytes:
    """Create a solid-color grayscale PNG."""
    img = Image.new("L", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_rgb_png(width: int, height: int, rgb: tuple[int, int, int] = (255, 255, 255)) -> bytes:
    """Create a solid-color RGB PNG."""
    img = Image.new("RGB", (width, height), rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_section(
    node_id: str = "1:1",
    node_name: str = "Hero",
    section_type: EmailSectionType = EmailSectionType.HERO,
    y_position: float = 0.0,
    height: float = 200.0,
    width: float = 600.0,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id=node_id,
        node_name=node_name,
        y_position=y_position,
        width=width,
        height=height,
        column_layout=ColumnLayout.SINGLE,
    )


def _make_layout(
    sections: list[EmailSection] | None = None,
) -> DesignLayoutDescription:
    return DesignLayoutDescription(
        file_name="test.fig",
        overall_width=600.0,
        sections=sections or [],
    )


# ── SSIM Scoring Engine Tests ──


class TestScoreFidelity:
    def test_identical_images_ssim_1(self) -> None:
        """Two identical solid-color PNGs should produce SSIM = 1.0."""
        png = _make_png(100, 100, color=128)
        sections = [_make_section(y_position=0, height=100)]
        result = score_fidelity(png, png, sections, blur_sigma=0)
        assert result.overall == 1.0
        assert len(result.sections) == 1
        assert result.sections[0].ssim == 1.0

    def test_completely_different_ssim_low(self) -> None:
        """White vs black image should produce very low SSIM."""
        white = _make_png(100, 100, color=255)
        black = _make_png(100, 100, color=0)
        sections = [_make_section(y_position=0, height=100)]
        result = score_fidelity(white, black, sections, blur_sigma=0)
        assert result.overall < 0.1

    def test_section_scores_match_layout(self) -> None:
        """3-section layout should produce 3 SectionScore entries."""
        png = _make_png(600, 300, color=128)
        sections = [
            _make_section(
                node_id="1:1",
                node_name="Header",
                section_type=EmailSectionType.HEADER,
                y_position=0,
                height=100,
            ),
            _make_section(
                node_id="1:2",
                node_name="Hero",
                section_type=EmailSectionType.HERO,
                y_position=100,
                height=100,
            ),
            _make_section(
                node_id="1:3",
                node_name="Footer",
                section_type=EmailSectionType.FOOTER,
                y_position=200,
                height=100,
            ),
        ]
        result = score_fidelity(png, png, sections, blur_sigma=0)
        assert len(result.sections) == 3
        assert result.sections[0].section_id == "1:1"
        assert result.sections[1].section_id == "1:2"
        assert result.sections[2].section_id == "1:3"
        for s in result.sections:
            assert s.ssim == 1.0

    def test_height_mismatch_pads(self) -> None:
        """Images with different heights should be padded, not crash."""
        short = _make_png(100, 50, color=128)
        tall = _make_png(100, 100, color=128)
        sections = [_make_section(y_position=0, height=100)]
        result = score_fidelity(short, tall, sections, blur_sigma=0)
        assert 0.0 <= result.overall <= 1.0

    def test_blur_reduces_aliasing_diff(self) -> None:
        """Applying blur should produce higher SSIM for slightly different images."""
        # Create two images that differ by a few pixels (simulating anti-aliasing)
        rng = np.random.default_rng(42)
        base = np.full((100, 100), 128, dtype=np.uint8)
        noisy = np.clip(base.astype(np.int16) + rng.integers(-10, 10, base.shape), 0, 255).astype(
            np.uint8
        )

        base_png = _array_to_png(base)
        noisy_png = _array_to_png(noisy)
        sections = [_make_section(y_position=0, height=100)]

        result_no_blur = score_fidelity(base_png, noisy_png, sections, blur_sigma=0)
        result_with_blur = score_fidelity(base_png, noisy_png, sections, blur_sigma=2.0)
        assert result_with_blur.overall >= result_no_blur.overall

    def test_diff_image_generated(self) -> None:
        """Non-identical images should produce a valid PNG diff image."""
        white = _make_png(100, 100, color=255)
        black = _make_png(100, 100, color=0)
        sections = [_make_section(y_position=0, height=100)]
        result = score_fidelity(white, black, sections, blur_sigma=0)
        assert result.diff_image is not None
        # Verify it's a valid PNG
        img = safe_image_open(io.BytesIO(result.diff_image))
        assert img.format == "PNG"
        assert img.size == (100, 100)

    def test_sections_with_none_position_skipped(self) -> None:
        """Sections without y_position should be skipped gracefully."""
        png = _make_png(100, 100, color=128)
        sections = [
            _make_section(y_position=None, height=None),  # type: ignore[arg-type]
        ]
        result = score_fidelity(png, png, sections, blur_sigma=0)
        assert len(result.sections) == 0
        # Overall falls back to full-image SSIM
        assert result.overall == 1.0


class TestClassifySeverity:
    def test_critical(self) -> None:
        assert classify_severity(0.60) == "critical"

    def test_warning(self) -> None:
        assert classify_severity(0.75) == "warning"

    def test_ok(self) -> None:
        assert classify_severity(0.90) == "ok"

    def test_exact_boundary_critical(self) -> None:
        assert classify_severity(0.70) == "warning"  # >= 0.70 is warning

    def test_exact_boundary_warning(self) -> None:
        assert classify_severity(0.85) == "ok"  # >= 0.85 is ok


class TestComputeDesignHeight:
    def test_empty_sections(self) -> None:
        assert _compute_design_height([]) == 0.0

    def test_single_section(self) -> None:
        sections = [_make_section(y_position=0, height=200)]
        assert _compute_design_height(sections) == 200.0

    def test_multiple_sections(self) -> None:
        sections = [
            _make_section(y_position=0, height=100),
            _make_section(y_position=100, height=150),
        ]
        assert _compute_design_height(sections) == 250.0


# ── Fidelity Service Tests ──


class TestVisualFidelityService:
    @pytest.mark.asyncio
    async def test_score_import_calls_figma_export(self) -> None:
        """Service should call export_images and download_image_bytes."""
        from app.design_sync.fidelity_service import VisualFidelityService
        from app.design_sync.protocol import ExportedImage

        svc = VisualFidelityService()
        design_import = MagicMock()
        design_import.id = 1
        connection = MagicMock()
        connection.file_ref = "abc123"
        connection.encrypted_token = "encrypted"
        user = MagicMock()
        layout = _make_layout(
            [
                _make_section(node_id="1:1", y_position=0, height=100),
                _make_section(node_id="1:2", y_position=100, height=100),
            ]
        )

        test_png = _make_rgb_png(600, 100, rgb=(128, 128, 128))

        mock_figma = AsyncMock()
        mock_figma.export_images.return_value = [
            ExportedImage(
                node_id="1:1", url="https://cdn.figma.com/1.png", format="png", expires_at=None
            ),
            ExportedImage(
                node_id="1:2", url="https://cdn.figma.com/2.png", format="png", expires_at=None
            ),
        ]
        mock_figma.download_image_bytes.return_value = test_png

        with (
            patch("app.design_sync.crypto.decrypt_token", return_value="decrypted-token"),
            patch(
                "app.rendering.local.runner.capture_screenshot",
                new_callable=AsyncMock,
                return_value=test_png,
            ),
            patch.object(svc, "_store_diff_image"),
        ):
            result = await svc.score_import(
                design_import,
                connection,
                "<html>test</html>",
                layout,
                user,
                figma_service=mock_figma,
            )

        assert isinstance(result, FidelityScore)
        assert 0.0 <= result.overall <= 1.0
        mock_figma.export_images.assert_called_once()
        assert mock_figma.download_image_bytes.call_count == 2

    @pytest.mark.asyncio
    async def test_score_import_calls_capture_screenshot(self) -> None:
        """Service should render HTML via capture_screenshot."""
        from app.design_sync.fidelity_service import VisualFidelityService
        from app.design_sync.protocol import ExportedImage

        svc = VisualFidelityService()
        design_import = MagicMock()
        design_import.id = 1
        connection = MagicMock()
        connection.file_ref = "abc123"
        user = MagicMock()
        layout = _make_layout([_make_section(node_id="1:1", y_position=0, height=200)])

        test_png = _make_rgb_png(600, 200, rgb=(200, 200, 200))
        mock_figma = AsyncMock()
        mock_figma.export_images.return_value = [
            ExportedImage(
                node_id="1:1", url="https://cdn.figma.com/1.png", format="png", expires_at=None
            ),
        ]
        mock_figma.download_image_bytes.return_value = test_png

        with (
            patch("app.design_sync.crypto.decrypt_token", return_value="decrypted-token"),
            patch(
                "app.rendering.local.runner.capture_screenshot",
                new_callable=AsyncMock,
                return_value=test_png,
            ) as mock_capture,
            patch.object(svc, "_store_diff_image"),
        ):
            await svc.score_import(
                design_import,
                connection,
                "<html>test</html>",
                layout,
                user,
                figma_service=mock_figma,
            )

        mock_capture.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_sections_raises(self) -> None:
        """Service should raise FidelityScoringError for empty sections."""
        from app.design_sync.exceptions import FidelityScoringError
        from app.design_sync.fidelity_service import VisualFidelityService

        svc = VisualFidelityService()
        layout = _make_layout([])

        with pytest.raises(FidelityScoringError, match="No sections"):
            await svc.score_import(
                MagicMock(),
                MagicMock(),
                "<html></html>",
                layout,
                MagicMock(),
            )


# ── Pipeline Integration Tests ──


class TestRunConversionFidelity:
    def test_run_conversion_accepts_score_fidelity_param(self) -> None:
        """run_conversion signature should accept score_fidelity kwarg."""
        import inspect

        from app.design_sync.import_service import DesignImportService

        sig = inspect.signature(DesignImportService.run_conversion)
        assert "score_fidelity" in sig.parameters
        param = sig.parameters["score_fidelity"]
        assert param.default is False

    def test_score_fidelity_on_convert_request_schema(self) -> None:
        """ConvertImportRequest should expose score_fidelity field."""
        from app.design_sync.schemas import ConvertImportRequest

        req = ConvertImportRequest()
        assert req.score_fidelity is False

        req_enabled = ConvertImportRequest(score_fidelity=True)
        assert req_enabled.score_fidelity is True

    def test_start_conversion_accepts_score_fidelity(self) -> None:
        """DesignSyncService.start_conversion should accept score_fidelity kwarg."""
        import inspect

        from app.design_sync.service import DesignSyncService

        sig = inspect.signature(DesignSyncService.start_conversion)
        assert "score_fidelity" in sig.parameters
        param = sig.parameters["score_fidelity"]
        assert param.default is False


# ── Schema Tests ──


class TestFidelitySchemas:
    def test_section_fidelity_score_schema(self) -> None:
        from app.design_sync.schemas import SectionFidelityScore

        score = SectionFidelityScore(
            section_id="1:1",
            section_name="Hero",
            section_type="hero",
            ssim=0.92,
            severity="ok",
        )
        assert score.ssim == 0.92
        assert score.severity == "ok"

    def test_fidelity_result_schema(self) -> None:
        from datetime import datetime

        from app.design_sync.schemas import FidelityResult, SectionFidelityScore

        result = FidelityResult(
            overall_ssim=0.87,
            sections=[
                SectionFidelityScore(
                    section_id="1:1",
                    section_name="Hero",
                    section_type="hero",
                    ssim=0.87,
                    severity="warning",
                ),
            ],
            diff_image_available=True,
            scored_at=datetime.now(tz=UTC),
        )
        assert result.overall_ssim == 0.87
        assert len(result.sections) == 1

    def test_fidelity_response_null_fidelity(self) -> None:
        from app.design_sync.schemas import FidelityResponse

        resp = FidelityResponse(import_id=1, fidelity=None)
        assert resp.fidelity is None


# ── Repository Tests ──


class TestRepositoryFidelity:
    @pytest.mark.asyncio
    async def test_fidelity_stored_in_import(self) -> None:
        """update_import_fidelity should set fidelity_json directly."""
        from app.design_sync.repository import DesignSyncRepository

        mock_db = AsyncMock()
        repo = DesignSyncRepository(mock_db)

        design_import = MagicMock()
        design_import.fidelity_json = None

        fidelity_data = {
            "overall_ssim": 0.85,
            "scored_at": "2026-03-27T12:00:00+00:00",
            "sections": [
                {
                    "section_id": "1:1",
                    "section_name": "Hero",
                    "section_type": "hero",
                    "ssim": 0.85,
                    "severity": "warning",
                }
            ],
            "diff_image_available": True,
        }

        await repo.update_import_fidelity(design_import, fidelity_data)

        assert design_import.fidelity_json is fidelity_data
        mock_db.commit.assert_called_once()


class TestSerializeScore:
    def test_serialize_score_includes_severity(self) -> None:
        """serialize_score should compute severity for each section."""
        from app.design_sync.fidelity_service import VisualFidelityService

        score = FidelityScore(
            overall=0.75,
            sections=[
                SectionScore(
                    section_id="1:1",
                    section_name="Hero",
                    section_type="hero",
                    ssim=0.60,
                    y_start=0,
                    y_end=200,
                ),
                SectionScore(
                    section_id="1:2",
                    section_name="Footer",
                    section_type="footer",
                    ssim=0.90,
                    y_start=200,
                    y_end=300,
                ),
            ],
            diff_image=b"fake-png",
        )

        data = VisualFidelityService.serialize_score(score)

        assert data["overall_ssim"] == 0.75
        assert data["diff_image_available"] is True
        assert len(data["sections"]) == 2
        assert data["sections"][0]["severity"] == "critical"  # 0.60 < 0.70
        assert data["sections"][1]["severity"] == "ok"  # 0.90 >= 0.85
        assert "scored_at" in data


# ── Edge Case Tests (Phase 35.11) ──


class TestScoreFidelityEdgeCases:
    def test_single_pixel_diff_high_score(self) -> None:
        """1-pixel difference produces score very close to 1.0."""
        base = np.full((100, 100), 128, dtype=np.uint8)
        modified = base.copy()
        modified[50, 50] = 200  # Change one pixel

        base_png = _array_to_png(base)
        modified_png = _array_to_png(modified)
        sections = [_make_section(y_position=0, height=100)]

        result = score_fidelity(base_png, modified_png, sections, blur_sigma=0)
        assert result.overall > 0.99

    def test_width_mismatch_handled(self) -> None:
        """Different width images are padded and produce valid score."""
        narrow = _make_png(80, 100, color=128)
        wide = _make_png(120, 100, color=128)
        sections = [_make_section(y_position=0, height=100)]

        result = score_fidelity(narrow, wide, sections, blur_sigma=0)
        assert 0.0 <= result.overall <= 1.0

    def test_empty_sections_overall_only(self) -> None:
        """Empty sections list → overall score only, no per-section breakdown."""
        png = _make_png(100, 100, color=128)
        result = score_fidelity(png, png, [], blur_sigma=0)

        assert result.overall == 1.0
        assert len(result.sections) == 0


# ── Utility ──


def _array_to_png(arr: np.ndarray) -> bytes:
    """Convert a numpy array to PNG bytes."""
    img = Image.fromarray(arr.astype(np.uint8), mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
