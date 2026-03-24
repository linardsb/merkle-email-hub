"""Visual regression testing — unit tests (mocked Playwright/ODiff)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.rendering.tests.visual_regression.baseline_generator import (
    BaselineGenerator,
)
from app.rendering.tests.visual_regression.regression_runner import (
    VisualRegressionRunner,
)
from app.rendering.tests.visual_regression.schemas import (
    ComparisonResult,
    RegressionReport,
)
from app.rendering.visual_diff import DiffResult

# Minimal 1x1 white PNG for mocking
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.visual_regression
class TestBaselineGenerator:
    """Tests for BaselineGenerator."""

    @patch(
        "app.rendering.tests.visual_regression.baseline_generator.capture_screenshot",
        new_callable=AsyncMock,
    )
    async def test_generates_baselines_for_templates_and_profiles(
        self, mock_capture: AsyncMock
    ) -> None:
        mock_capture.return_value = _TINY_PNG

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir)
            gen = BaselineGenerator()
            manifest = await gen.generate_baselines(
                templates=["minimal_text"],
                profiles=["gmail_web"],
                output_dir=output,
            )

            assert len(manifest.baselines) == 1
            assert manifest.baselines[0].template_slug == "minimal_text"
            assert manifest.baselines[0].profile_id == "gmail_web"
            assert (output / "minimal_text" / "gmail_web.png").exists()

            # Manifest JSON written
            manifest_path = output / "manifest.json"
            assert manifest_path.exists()
            data = json.loads(manifest_path.read_text())
            assert data["baseline_count"] == 1

    @patch(
        "app.rendering.tests.visual_regression.baseline_generator.capture_screenshot",
        new_callable=AsyncMock,
    )
    async def test_skips_unknown_profile(self, mock_capture: AsyncMock) -> None:
        mock_capture.return_value = _TINY_PNG

        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BaselineGenerator()
            manifest = await gen.generate_baselines(
                templates=["minimal_text"],
                profiles=["nonexistent_profile"],
                output_dir=Path(tmpdir),
            )
            assert len(manifest.baselines) == 0

    @patch(
        "app.rendering.tests.visual_regression.baseline_generator.capture_screenshot",
        new_callable=AsyncMock,
    )
    async def test_continues_on_capture_failure(self, mock_capture: AsyncMock) -> None:
        mock_capture.side_effect = [OSError("display fail"), _TINY_PNG]

        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BaselineGenerator()
            manifest = await gen.generate_baselines(
                templates=["minimal_text"],
                profiles=["gmail_web", "apple_mail"],
                output_dir=Path(tmpdir),
            )
            # One failed, one succeeded
            assert len(manifest.baselines) == 1
            assert manifest.baselines[0].profile_id == "apple_mail"


@pytest.mark.visual_regression
class TestRegressionRunner:
    """Tests for VisualRegressionRunner."""

    async def test_passes_when_baselines_match(self) -> None:
        """All baselines match current output -> passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baselines = Path(tmpdir)
            # Create a baseline
            tpl_dir = baselines / "minimal_text"
            tpl_dir.mkdir()
            (tpl_dir / "gmail_web.png").write_bytes(_TINY_PNG)
            # Create manifest
            (baselines / "manifest.json").write_text(
                json.dumps(
                    {
                        "templates": ["minimal_text"],
                        "profiles": ["gmail_web"],
                    }
                )
            )

            runner = VisualRegressionRunner(baseline_dir=baselines, threshold=0.5)

            with (
                patch(
                    "app.rendering.tests.visual_regression.regression_runner.capture_screenshot",
                    new_callable=AsyncMock,
                    return_value=_TINY_PNG,
                ),
                patch(
                    "app.rendering.tests.visual_regression.regression_runner.run_odiff",
                    new_callable=AsyncMock,
                    return_value=DiffResult(
                        identical=True,
                        diff_percentage=0.0,
                        diff_image=None,
                        pixel_count=0,
                        changed_regions=[],
                    ),
                ),
            ):
                report = await runner.run()

            assert report.passed is True
            assert report.total == 1
            assert len(report.failures) == 0

    async def test_detects_regression_above_threshold(self) -> None:
        """Modified emulator rule -> detects regression for affected clients."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baselines = Path(tmpdir)
            tpl_dir = baselines / "promotional_hero"
            tpl_dir.mkdir()
            (tpl_dir / "gmail_web.png").write_bytes(_TINY_PNG)
            (baselines / "manifest.json").write_text(
                json.dumps(
                    {
                        "templates": ["promotional_hero"],
                        "profiles": ["gmail_web"],
                    }
                )
            )

            runner = VisualRegressionRunner(baseline_dir=baselines, threshold=0.5)

            diff_image_bytes = b"fake-diff-png"
            with (
                patch(
                    "app.rendering.tests.visual_regression.regression_runner.capture_screenshot",
                    new_callable=AsyncMock,
                    return_value=_TINY_PNG,
                ),
                patch(
                    "app.rendering.tests.visual_regression.regression_runner.run_odiff",
                    new_callable=AsyncMock,
                    return_value=DiffResult(
                        identical=False,
                        diff_percentage=2.3,
                        diff_image=diff_image_bytes,
                        pixel_count=1500,
                        changed_regions=[],
                    ),
                ),
            ):
                report = await runner.run()

            assert report.passed is False
            assert len(report.failures) == 1
            assert report.failures[0].diff_percentage == 2.3
            assert report.failures[0].diff_image_path is not None

    async def test_skips_profile_with_no_baseline(self) -> None:
        """New emulator rule with no baseline -> skipped (not failed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baselines = Path(tmpdir)
            (baselines / "manifest.json").write_text(
                json.dumps(
                    {
                        "templates": ["minimal_text"],
                        "profiles": ["brand_new_client"],
                    }
                )
            )

            runner = VisualRegressionRunner(baseline_dir=baselines, threshold=0.5)
            report = await runner.run()

            assert report.passed is True
            assert report.total == 0
            assert "minimal_text" in report.skipped

    async def test_threshold_override(self) -> None:
        """Threshold override via constructor."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baselines = Path(tmpdir)
            tpl_dir = baselines / "minimal_text"
            tpl_dir.mkdir()
            (tpl_dir / "gmail_web.png").write_bytes(_TINY_PNG)
            (baselines / "manifest.json").write_text(
                json.dumps(
                    {
                        "templates": ["minimal_text"],
                        "profiles": ["gmail_web"],
                    }
                )
            )

            # High threshold — 2.3% diff should pass
            runner = VisualRegressionRunner(baseline_dir=baselines, threshold=5.0)

            with (
                patch(
                    "app.rendering.tests.visual_regression.regression_runner.capture_screenshot",
                    new_callable=AsyncMock,
                    return_value=_TINY_PNG,
                ),
                patch(
                    "app.rendering.tests.visual_regression.regression_runner.run_odiff",
                    new_callable=AsyncMock,
                    return_value=DiffResult(
                        identical=False,
                        diff_percentage=2.3,
                        diff_image=None,
                        pixel_count=100,
                        changed_regions=[],
                    ),
                ),
            ):
                report = await runner.run()

            assert report.passed is True

    async def test_no_manifest_returns_pass(self) -> None:
        """No manifest.json -> empty pass (first run, no baselines yet)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = VisualRegressionRunner(baseline_dir=Path(tmpdir), threshold=0.5)
            report = await runner.run()
            assert report.passed is True
            assert report.total == 0

    async def test_report_properties(self) -> None:
        """RegressionReport properties work correctly."""
        r1 = ComparisonResult(
            template="a",
            profile="b",
            diff_percentage=0.0,
            passed=True,
            diff_image_path=None,
        )
        r2 = ComparisonResult(
            template="c",
            profile="d",
            diff_percentage=5.0,
            passed=False,
            diff_image_path=Path("/tmp/diff.png"),
        )
        report = RegressionReport(
            passed=False,
            threshold=0.5,
            results=[r1, r2],
        )
        assert report.total == 2
        assert len(report.failures) == 1
        assert report.failures[0].template == "c"
