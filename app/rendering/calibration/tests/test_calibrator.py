"""Tests for emulator calibration."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rendering.calibration.calibrator import EmulatorCalibrator, _emulator_version_hash


class TestEmulatorVersionHash:
    """Tests for _emulator_version_hash helper."""

    def test_known_emulator_returns_hex(self) -> None:
        result = _emulator_version_hash("gmail_web")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_unknown_emulator_returns_no_emulator(self) -> None:
        result = _emulator_version_hash("nonexistent_client")
        assert result == "no-emulator"

    def test_deterministic(self) -> None:
        a = _emulator_version_hash("gmail_web")
        b = _emulator_version_hash("gmail_web")
        assert a == b

    def test_different_emulators_differ(self) -> None:
        gmail = _emulator_version_hash("gmail_web")
        outlook = _emulator_version_hash("outlook_desktop")
        assert gmail != outlook


@dataclass
class _FakeImageResult:
    identical: bool
    diff_percentage: float
    pixel_count: int
    diff_image: bytes | None = None
    changed_regions: list[tuple[int, int, int, int]] = ()  # type: ignore[assignment]


class TestEmulatorCalibrator:
    """Tests for EmulatorCalibrator."""

    @pytest.fixture()
    def db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def calibrator(self, db: AsyncMock) -> EmulatorCalibrator:
        return EmulatorCalibrator(db)

    @pytest.mark.asyncio()
    async def test_identical_images_full_accuracy(self, calibrator: EmulatorCalibrator) -> None:
        fake_result = _FakeImageResult(identical=True, diff_percentage=0.0, pixel_count=0)

        with (
            patch("app.rendering.calibration.calibrator.compare_images", return_value=fake_result),
            patch.object(calibrator.repo, "get_summary", return_value=None),
            patch.object(calibrator.repo, "create_record", new_callable=AsyncMock),
        ):
            result = await calibrator.calibrate(
                html="<html>test</html>",
                client_id="gmail_web",
                local_screenshot=b"img1",
                external_screenshot=b"img2",
                external_provider="sandbox",
            )

        assert result.diff_percentage == 0.0
        assert result.accuracy_score == 100.0
        assert result.regression is False

    @pytest.mark.asyncio()
    async def test_50_pct_diff_zero_accuracy(self, calibrator: EmulatorCalibrator) -> None:
        fake_result = _FakeImageResult(identical=False, diff_percentage=50.0, pixel_count=50000)

        with (
            patch("app.rendering.calibration.calibrator.compare_images", return_value=fake_result),
            patch.object(calibrator.repo, "get_summary", return_value=None),
            patch.object(calibrator.repo, "create_record", new_callable=AsyncMock),
        ):
            result = await calibrator.calibrate(
                html="<html>test</html>",
                client_id="gmail_web",
                local_screenshot=b"img1",
                external_screenshot=b"img2",
                external_provider="sandbox",
            )

        assert result.diff_percentage == 50.0
        assert result.accuracy_score == 0.0

    @pytest.mark.asyncio()
    async def test_regression_detected(self, calibrator: EmulatorCalibrator) -> None:
        fake_result = _FakeImageResult(identical=False, diff_percentage=30.0, pixel_count=30000)
        mock_summary = MagicMock()
        mock_summary.current_accuracy = 80.0
        mock_summary.sample_count = 5

        with (
            patch("app.rendering.calibration.calibrator.compare_images", return_value=fake_result),
            patch.object(calibrator.repo, "get_summary", return_value=mock_summary),
            patch.object(calibrator.repo, "create_record", new_callable=AsyncMock),
        ):
            result = await calibrator.calibrate(
                html="<html>test</html>",
                client_id="gmail_web",
                local_screenshot=b"img1",
                external_screenshot=b"img2",
                external_provider="sandbox",
            )

        # 30% diff → accuracy 40%. Drop from 80 → 40 = 40% > threshold 10%
        assert result.accuracy_score == 40.0
        assert result.regression is True
        assert result.regression_details is not None

    @pytest.mark.asyncio()
    async def test_batch_matches_by_client_id(self, calibrator: EmulatorCalibrator) -> None:
        fake_result = _FakeImageResult(identical=True, diff_percentage=0.0, pixel_count=0)

        with (
            patch("app.rendering.calibration.calibrator.compare_images", return_value=fake_result),
            patch.object(calibrator.repo, "get_summary", return_value=None),
            patch.object(calibrator.repo, "create_record", new_callable=AsyncMock),
        ):
            results = await calibrator.calibrate_batch(
                html="<html>test</html>",
                local_screenshots={"gmail_web": b"img1", "yahoo_web": b"img2"},
                external_screenshots={"gmail_web": b"ext1", "thunderbird": b"ext3"},
                external_provider="sandbox",
            )

        # Only gmail_web matched
        assert len(results) == 1
        assert results[0].client_id == "gmail_web"

    @pytest.mark.asyncio()
    async def test_ema_update(self, calibrator: EmulatorCalibrator) -> None:
        mock_summary = MagicMock()
        mock_summary.current_accuracy = 80.0
        mock_summary.sample_count = 5
        mock_summary.accuracy_trend = [78.0, 79.0, 80.0]
        mock_summary.known_blind_spots = ["blind1"]

        from app.rendering.calibration.schemas import CalibrationResultSchema

        result = CalibrationResultSchema(
            client_id="gmail_web",
            diff_percentage=5.0,
            accuracy_score=90.0,
            pixel_count=100,
        )

        with (
            patch.object(calibrator.repo, "get_summary", return_value=mock_summary),
            patch.object(calibrator.repo, "upsert_summary", new_callable=AsyncMock) as mock_upsert,
        ):
            await calibrator.update_seeds([result], external_provider="sandbox")

        # EMA: 0.7 * 80 + 0.3 * 90 = 83.0
        call_kwargs = mock_upsert.call_args.kwargs
        assert call_kwargs["current_accuracy"] == 83.0
        assert call_kwargs["sample_count"] == 6
        assert call_kwargs["last_provider"] == "sandbox"
