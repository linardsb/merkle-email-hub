"""Tests for calibration sampler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rendering.calibration.sampler import CalibrationSampler


class TestCalibrationSampler:
    """Tests for CalibrationSampler."""

    @pytest.fixture()
    def db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def sampler(self, db: AsyncMock) -> CalibrationSampler:
        return CalibrationSampler(db)

    @pytest.mark.asyncio()
    async def test_disabled_returns_false(self, sampler: CalibrationSampler) -> None:
        with patch(
            "app.rendering.calibration.sampler.settings.rendering.calibration.enabled",
            False,
        ):
            result = await sampler.should_calibrate("gmail_web")
        assert result is False

    @pytest.mark.asyncio()
    async def test_under_rate_limit_returns_true(self, sampler: CalibrationSampler) -> None:
        with (
            patch(
                "app.rendering.calibration.sampler.settings.rendering.calibration.enabled",
                True,
            ),
            patch(
                "app.rendering.calibration.sampler.settings.rendering.calibration.rate_per_client_per_day",
                3,
            ),
            patch.object(sampler.repo, "count_today", return_value=0),
            patch.object(sampler.repo, "get_summary", return_value=None),
        ):
            result = await sampler.should_calibrate("gmail_web")
        # New emulator (no summary) → 3x rate → 0 < 9 → True
        assert result is True

    @pytest.mark.asyncio()
    async def test_at_rate_limit_returns_false(self, sampler: CalibrationSampler) -> None:
        mock_summary = MagicMock()
        mock_summary.sample_count = 20
        mock_summary.updated_at = None

        with (
            patch(
                "app.rendering.calibration.sampler.settings.rendering.calibration.enabled",
                True,
            ),
            patch(
                "app.rendering.calibration.sampler.settings.rendering.calibration.rate_per_client_per_day",
                3,
            ),
            patch.object(sampler.repo, "count_today", return_value=3),
            patch.object(sampler.repo, "get_summary", return_value=mock_summary),
        ):
            result = await sampler.should_calibrate("gmail_web")
        # Mature emulator, at limit → 3 >= 3 → False
        assert result is False

    def test_select_deduplicates_and_respects_max(self, sampler: CalibrationSampler) -> None:
        candidates = [
            "<html>A</html>",
            "<html>B</html>",
            "<html>A</html>",  # duplicate
            "<html>C</html>",
        ]
        selected = sampler.select_html_for_calibration(candidates, "gmail_web", max_selections=2)
        assert len(selected) == 2
        assert selected[0] == "<html>A</html>"
        assert selected[1] == "<html>B</html>"
