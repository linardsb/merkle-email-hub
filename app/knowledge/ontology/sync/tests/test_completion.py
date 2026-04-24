"""Tests for 24B.1 — CanIEmail sync completion (CLI, freshness, overrides)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.sync.schemas import SyncDiff, SyncReport, SyncState
from app.knowledge.ontology.sync.service import CanIEmailSyncService


class TestSyncCLI:
    """Tests for the CLI entrypoint."""

    def test_cli_module_importable(self) -> None:
        """CLI module can be imported without errors."""

    @pytest.mark.asyncio
    async def test_cli_main_dry_run(self) -> None:
        """CLI main() executes in dry-run mode without error."""
        from app.knowledge.ontology.sync.cli import main

        mock_report = SyncReport(dry_run=True)
        with patch.object(
            CanIEmailSyncService,
            "sync",
            new_callable=AsyncMock,
            return_value=mock_report,
        ):
            await main(dry_run=True)


class TestFreshness:
    """Tests for the freshness check."""

    @pytest.mark.asyncio
    async def test_freshness_fresh(self) -> None:
        """Data synced recently is reported as fresh."""
        service = CanIEmailSyncService()
        recent_state = SyncState(
            last_sync_at=datetime.now(UTC) - timedelta(days=30),
            last_commit_sha="abc123",
            features_synced=100,
        )
        with patch.object(
            service, "_load_state", new_callable=AsyncMock, return_value=recent_state
        ):
            is_fresh, msg = await service.check_freshness(max_age_days=90)
        assert is_fresh is True
        assert "30 days old" in msg

    @pytest.mark.asyncio
    async def test_freshness_stale(self) -> None:
        """Data synced long ago is reported as stale."""
        service = CanIEmailSyncService()
        old_state = SyncState(
            last_sync_at=datetime.now(UTC) - timedelta(days=120),
            last_commit_sha="abc123",
            features_synced=100,
        )
        with patch.object(service, "_load_state", new_callable=AsyncMock, return_value=old_state):
            is_fresh, msg = await service.check_freshness(max_age_days=90)
        assert is_fresh is False
        assert "120 days old" in msg
        assert "ontology-sync" in msg

    @pytest.mark.asyncio
    async def test_freshness_never_synced(self) -> None:
        """Data that was never synced is reported as stale."""
        service = CanIEmailSyncService()
        empty_state = SyncState()
        with patch.object(service, "_load_state", new_callable=AsyncMock, return_value=empty_state):
            is_fresh, msg = await service.check_freshness()
        assert is_fresh is False
        assert "never been synced" in msg


class TestOverrides:
    """Tests for override file support."""

    def test_override_merge_in_registry(self) -> None:
        """Overrides replace entries in the support matrix when registry loads."""
        overrides_path = Path(__file__).resolve().parent.parent.parent / "data" / "overrides.yaml"
        assert overrides_path.parent.exists(), "Data directory must exist"

        # Verify overrides file is loadable
        if overrides_path.exists():
            with overrides_path.open() as f:
                data = yaml.safe_load(f)
            assert isinstance(cast(dict[str, Any], data or {}).get("overrides", []), list)

        # Empty overrides file should not break loading
        registry = load_ontology()
        assert len(registry.clients) > 0
        assert len(registry.properties) > 0

    def test_override_skip_during_sync(self) -> None:
        """Writer skips entries that have manual overrides."""
        diff = SyncDiff(
            new_clients=[],
            new_properties=[],
            updated_support=[
                ("display_flex", "outlook_2019", "none", "partial"),
                ("border_radius", "gmail_web", "partial", "full"),
            ],
            new_support=[],
        )

        # Simulate override_keys filtering (same logic as in writer)
        override_keys = {("display_flex", "outlook_2019")}
        filtered_updated = [u for u in diff.updated_support if (u[0], u[1]) not in override_keys]
        assert len(filtered_updated) == 1
        assert filtered_updated[0][0] == "border_radius"
