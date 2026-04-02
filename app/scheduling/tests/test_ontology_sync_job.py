"""Tests for the scheduled ontology sync job."""

from __future__ import annotations

import importlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduling.registry import get_registry


class TestOntologySyncRegistration:
    def test_ontology_sync_registered(self) -> None:
        """ontology_sync appears in the registry with correct cron."""
        import app.scheduling.jobs.ontology_sync as mod

        importlib.reload(mod)

        registry = get_registry()
        assert "ontology_sync" in registry
        _, cron = registry["ontology_sync"]
        assert cron == "0 3 * * 0"


class TestOntologySyncExecution:
    @pytest.fixture()
    def _mock_settings(self) -> MagicMock:
        settings = MagicMock()
        settings.ontology_sync.enabled = True
        settings.ontology_sync.dry_run = False
        return settings

    async def test_ontology_sync_runs_service(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """Enabled → CanIEmailSyncService.sync() called, result stored in Redis."""
        mock_report = MagicMock()
        mock_report.new_properties = 3
        mock_report.updated_levels = 5
        mock_report.new_clients = 1
        mock_report.errors = []
        mock_report.commit_sha = "abc123"
        mock_report.dry_run = False

        mock_service = AsyncMock()
        mock_service.sync = AsyncMock(return_value=mock_report)

        with (
            patch(
                "app.scheduling.jobs.ontology_sync.get_settings",
                return_value=_mock_settings,
            ),
            patch(
                "app.scheduling.jobs.ontology_sync.get_redis",
                return_value=mock_redis,
            ),
            patch(
                "app.scheduling.jobs.ontology_sync.CanIEmailSyncService",
                return_value=mock_service,
            ),
        ):
            from app.scheduling.jobs.ontology_sync import ontology_sync

            await ontology_sync()

        mock_service.sync.assert_awaited_once_with(dry_run=False)
        # date key + latest key
        assert mock_redis.set.call_count == 2
        # Verify stored payload contains report fields
        date_call = mock_redis.set.call_args_list[0]
        result = json.loads(date_call[0][1])
        assert result["new_properties"] == 3
        assert result["updated_levels"] == 5
        assert result["new_clients"] == 1
        assert result["commit_sha"] == "abc123"
        assert date_call[1]["ex"] == 30 * 86400

    async def test_ontology_sync_skips_when_disabled(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """enabled=False → service never instantiated."""
        _mock_settings.ontology_sync.enabled = False

        with (
            patch(
                "app.scheduling.jobs.ontology_sync.get_settings",
                return_value=_mock_settings,
            ),
            patch(
                "app.scheduling.jobs.ontology_sync.CanIEmailSyncService",
            ) as mock_svc_cls,
        ):
            from app.scheduling.jobs.ontology_sync import ontology_sync

            await ontology_sync()

        mock_svc_cls.assert_not_called()
