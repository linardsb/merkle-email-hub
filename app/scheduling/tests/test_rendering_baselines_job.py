"""Tests for the scheduled rendering baselines job."""

from __future__ import annotations

import importlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduling.registry import get_registry


class TestRenderingBaselinesRegistration:
    def test_rendering_baselines_registered(self) -> None:
        """rendering_baselines appears in the registry with correct cron."""
        import app.scheduling.jobs.rendering_baselines as mod

        importlib.reload(mod)

        registry = get_registry()
        assert "rendering_baselines" in registry
        _, cron = registry["rendering_baselines"]
        assert cron == "0 4 1,15 * *"


class TestRenderingBaselinesExecution:
    @pytest.fixture()
    def _mock_settings(self) -> MagicMock:
        settings = MagicMock()
        settings.rendering.provider = "litmus"
        return settings

    async def test_rendering_baselines_runs_generator(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """Non-mock provider → BaselineGenerator.generate_baselines() called, stored."""
        mock_manifest = MagicMock()
        mock_manifest.baselines = [MagicMock(), MagicMock(), MagicMock()]
        mock_manifest.template_slugs = ["minimal_text", "promotional_hero"]
        mock_manifest.profile_ids = ["gmail", "outlook"]
        mock_manifest.emulator_versions = {"gmail": "abc123", "outlook": "def456"}

        mock_generator = AsyncMock()
        mock_generator.generate_baselines = AsyncMock(return_value=mock_manifest)

        with (
            patch(
                "app.scheduling.jobs.rendering_baselines.get_settings",
                return_value=_mock_settings,
            ),
            patch(
                "app.scheduling.jobs.rendering_baselines.get_redis",
                return_value=mock_redis,
            ),
            patch(
                "app.scheduling.jobs.rendering_baselines.BaselineGenerator",
                return_value=mock_generator,
            ),
        ):
            from app.scheduling.jobs.rendering_baselines import rendering_baselines

            await rendering_baselines()

        mock_generator.generate_baselines.assert_awaited_once()
        # date key + latest key
        assert mock_redis.set.call_count == 2
        # Verify stored payload contains manifest fields
        date_call = mock_redis.set.call_args_list[0]
        result = json.loads(date_call[0][1])
        assert result["baseline_count"] == 3
        assert result["template_slugs"] == ["minimal_text", "promotional_hero"]
        assert result["profile_ids"] == ["gmail", "outlook"]
        assert date_call[1]["ex"] == 30 * 86400

    async def test_rendering_baselines_skips_mock_provider(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """provider='mock' → generator never instantiated."""
        _mock_settings.rendering.provider = "mock"

        with (
            patch(
                "app.scheduling.jobs.rendering_baselines.get_settings",
                return_value=_mock_settings,
            ),
            patch(
                "app.scheduling.jobs.rendering_baselines.BaselineGenerator",
            ) as mock_gen_cls,
        ):
            from app.scheduling.jobs.rendering_baselines import rendering_baselines

            await rendering_baselines()

        mock_gen_cls.assert_not_called()
