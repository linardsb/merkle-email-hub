"""Tests for CanIEmailSyncService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.knowledge.ontology.sync.schemas import (
    CanIEmailFeature,
    SyncDiff,
    SyncState,
)
from app.knowledge.ontology.sync.service import CanIEmailSyncService


def _make_feature(slug: str = "css-display-flex") -> CanIEmailFeature:
    return CanIEmailFeature(
        slug=slug,
        title="display:flex",
        category="css",
        last_test_date="2024-01-01",
        stats={"gmail": {"desktop-webmail": {"2024-01": "y"}}},
        notes={},
    )


@pytest.fixture()
def service() -> CanIEmailSyncService:
    with patch("app.knowledge.ontology.sync.caniemail_client.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.ontology_sync.github_repo = "hteumeuleu/caniemail"
        settings.ontology_sync.github_branch = "main"
        settings.ontology_sync.request_timeout_seconds = 10
        settings.ontology_sync.max_features_per_sync = 500
        settings.ontology_sync.github_token = ""
        return CanIEmailSyncService()


class TestSync:
    @pytest.mark.anyio()
    async def test_dry_run_does_not_write(self, service: CanIEmailSyncService) -> None:
        service._client.get_latest_commit_sha = AsyncMock(return_value="abc123")
        service._client.fetch_all_features = AsyncMock(return_value=[_make_feature()])

        with (
            patch("app.knowledge.ontology.sync.service.load_ontology") as mock_load,
            patch("app.knowledge.ontology.sync.service.compute_diff") as mock_diff,
            patch("app.knowledge.ontology.sync.service.apply_sync") as mock_apply,
        ):
            mock_load.return_value = MagicMock()
            mock_diff.return_value = SyncDiff(new_properties=["display_flex"])
            service._save_state = AsyncMock()  # type: ignore[method-assign]
            service._save_report = AsyncMock()  # type: ignore[method-assign]

            report = await service.sync(dry_run=True)

        assert report.dry_run is True
        assert report.new_properties == 1
        mock_apply.assert_not_called()
        service._save_state.assert_not_awaited()

    @pytest.mark.anyio()
    async def test_real_sync_applies_changes(self, service: CanIEmailSyncService) -> None:
        service._client.get_latest_commit_sha = AsyncMock(return_value="abc123")
        service._client.fetch_all_features = AsyncMock(return_value=[_make_feature()])

        with (
            patch("app.knowledge.ontology.sync.service.load_ontology") as mock_load,
            patch("app.knowledge.ontology.sync.service.compute_diff") as mock_diff,
            patch("app.knowledge.ontology.sync.service.apply_sync") as mock_apply,
        ):
            mock_load.return_value = MagicMock()
            diff = SyncDiff(
                updated_support=[("display_flex", "gmail_web", "none", "full")],
            )
            mock_diff.return_value = diff
            service._save_state = AsyncMock()  # type: ignore[method-assign]
            service._save_report = AsyncMock()  # type: ignore[method-assign]

            report = await service.sync(dry_run=False)

        assert report.dry_run is False
        assert report.updated_levels == 1
        assert len(report.changelog) == 1
        assert report.changelog[0].old_level == "none"
        assert report.changelog[0].new_level == "full"
        mock_apply.assert_called_once()
        service._save_state.assert_awaited_once()

    @pytest.mark.anyio()
    async def test_fetch_sha_failure_returns_error(self, service: CanIEmailSyncService) -> None:
        service._client.get_latest_commit_sha = AsyncMock(side_effect=Exception("Network error"))
        service._save_report = AsyncMock()  # type: ignore[method-assign]

        report = await service.sync(dry_run=False)

        assert len(report.errors) == 1
        assert "commit SHA" in report.errors[0]

    @pytest.mark.anyio()
    async def test_fetch_features_failure_returns_error(
        self, service: CanIEmailSyncService
    ) -> None:
        service._client.get_latest_commit_sha = AsyncMock(return_value="abc123")
        service._client.fetch_all_features = AsyncMock(side_effect=Exception("Timeout"))
        service._save_report = AsyncMock()  # type: ignore[method-assign]

        report = await service.sync(dry_run=False)

        assert len(report.errors) == 1
        assert "features" in report.errors[0]

    @pytest.mark.anyio()
    async def test_no_changes_report(self, service: CanIEmailSyncService) -> None:
        service._client.get_latest_commit_sha = AsyncMock(return_value="abc123")
        service._client.fetch_all_features = AsyncMock(return_value=[])

        with (
            patch("app.knowledge.ontology.sync.service.load_ontology") as mock_load,
            patch("app.knowledge.ontology.sync.service.compute_diff") as mock_diff,
            patch("app.knowledge.ontology.sync.service.apply_sync") as mock_apply,
        ):
            mock_load.return_value = MagicMock()
            mock_diff.return_value = SyncDiff()  # No changes
            service._save_state = AsyncMock()  # type: ignore[method-assign]
            service._save_report = AsyncMock()  # type: ignore[method-assign]

            report = await service.sync(dry_run=False)

        assert report.new_properties == 0
        assert report.updated_levels == 0
        assert len(report.changelog) == 0
        mock_apply.assert_not_called()

    @pytest.mark.anyio()
    async def test_new_support_entries_in_changelog(self, service: CanIEmailSyncService) -> None:
        service._client.get_latest_commit_sha = AsyncMock(return_value="abc123")
        service._client.fetch_all_features = AsyncMock(return_value=[_make_feature()])

        with (
            patch("app.knowledge.ontology.sync.service.load_ontology") as mock_load,
            patch("app.knowledge.ontology.sync.service.compute_diff") as mock_diff,
            patch("app.knowledge.ontology.sync.service.apply_sync"),
        ):
            mock_load.return_value = MagicMock()
            diff = SyncDiff(
                new_support=[("display_flex", "gmail_web", "full")],
            )
            mock_diff.return_value = diff
            service._save_state = AsyncMock()  # type: ignore[method-assign]
            service._save_report = AsyncMock()  # type: ignore[method-assign]

            report = await service.sync(dry_run=True)

        assert len(report.changelog) == 1
        assert report.changelog[0].old_level is None
        assert report.changelog[0].new_level == "full"


class TestGetStatus:
    @pytest.mark.anyio()
    async def test_returns_status(self, service: CanIEmailSyncService) -> None:
        from datetime import UTC, datetime

        state = SyncState(
            last_sync_at=datetime(2024, 1, 1, tzinfo=UTC),
            last_commit_sha="abc123",
            features_synced=100,
        )
        service._load_state = AsyncMock(return_value=state)  # type: ignore[method-assign]
        service._load_report = AsyncMock(return_value={"new_properties": 5})  # type: ignore[method-assign]

        status = await service.get_status()

        assert status.last_commit_sha == "abc123"
        assert status.features_synced == 100
        assert status.last_report == {"new_properties": 5}

    @pytest.mark.anyio()
    async def test_returns_empty_status(self, service: CanIEmailSyncService) -> None:
        service._load_state = AsyncMock(return_value=SyncState())  # type: ignore[method-assign]
        service._load_report = AsyncMock(return_value=None)  # type: ignore[method-assign]

        status = await service.get_status()

        assert status.last_sync_at is None
        assert status.last_commit_sha is None
        assert status.last_report is None


class TestSyncIdempotency:
    @pytest.mark.anyio()
    async def test_second_sync_same_data_empty_changelog(
        self, service: CanIEmailSyncService
    ) -> None:
        """Running sync twice with identical data returns empty changelog the second time."""
        service._client.get_latest_commit_sha = AsyncMock(return_value="abc123")
        service._client.fetch_all_features = AsyncMock(return_value=[_make_feature()])

        with (
            patch("app.knowledge.ontology.sync.service.load_ontology") as mock_load,
            patch("app.knowledge.ontology.sync.service.compute_diff") as mock_diff,
            patch("app.knowledge.ontology.sync.service.apply_sync"),
        ):
            mock_load.return_value = MagicMock()
            # First sync has changes
            mock_diff.return_value = SyncDiff(
                new_support=[("display_flex", "gmail_web", "full")],
            )
            service._save_state = AsyncMock()  # type: ignore[method-assign]
            service._save_report = AsyncMock()  # type: ignore[method-assign]
            report1 = await service.sync(dry_run=False)

            # Second sync with same data — no changes
            mock_diff.return_value = SyncDiff()
            report2 = await service.sync(dry_run=False)

        assert len(report1.changelog) == 1
        assert len(report2.changelog) == 0
        assert report2.new_properties == 0
        assert report2.updated_levels == 0

    @pytest.mark.anyio()
    async def test_multiple_errors_collected(
        self, service: CanIEmailSyncService
    ) -> None:
        """Multiple failures during sync are all collected in errors list."""
        service._client.get_latest_commit_sha = AsyncMock(return_value="abc123")
        service._client.fetch_all_features = AsyncMock(
            side_effect=Exception("Feature fetch failed")
        )
        service._save_report = AsyncMock()  # type: ignore[method-assign]

        report = await service.sync(dry_run=False)

        assert len(report.errors) >= 1
        assert report.new_properties == 0
        assert report.updated_levels == 0
