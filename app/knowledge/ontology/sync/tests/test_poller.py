"""Tests for CanIEmailSyncPoller."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from app.knowledge.ontology.sync.poller import CanIEmailSyncPoller
from app.knowledge.ontology.sync.schemas import SyncReport


@pytest.fixture()
def poller() -> Generator[CanIEmailSyncPoller, None, None]:
    with patch("app.knowledge.ontology.sync.poller.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.ontology_sync.interval_hours = 168
        settings.ontology_sync.dry_run = True
        settings.cognee.enabled = False

        with patch(
            "app.knowledge.ontology.sync.caniemail_client.get_settings",
            return_value=settings,
        ):
            settings.ontology_sync.github_repo = "hteumeuleu/caniemail"
            settings.ontology_sync.github_branch = "main"
            settings.ontology_sync.request_timeout_seconds = 10
            settings.ontology_sync.max_features_per_sync = 500
            settings.ontology_sync.github_token = ""
            yield CanIEmailSyncPoller()


class TestFetch:
    @pytest.mark.anyio()
    async def test_delegates_to_service(self, poller: CanIEmailSyncPoller) -> None:
        expected_report = SyncReport(new_properties=3, dry_run=True, commit_sha="abc123")
        poller._service.sync = AsyncMock(return_value=expected_report)  # type: ignore[method-assign]

        result = await poller.fetch()

        assert result is expected_report
        poller._service.sync.assert_awaited_once_with(dry_run=True)

    @pytest.mark.anyio()
    async def test_passes_dry_run_from_config(self, poller: CanIEmailSyncPoller) -> None:
        poller._dry_run = False
        poller._service.sync = AsyncMock(return_value=SyncReport())  # type: ignore[method-assign]

        await poller.fetch()

        poller._service.sync.assert_awaited_once_with(dry_run=False)


class TestEnrich:
    @pytest.mark.anyio()
    async def test_passthrough(self, poller: CanIEmailSyncPoller) -> None:
        report = SyncReport(new_properties=1)
        result = await poller.enrich(report)
        assert result is report


class TestStore:
    @pytest.mark.anyio()
    async def test_logs_and_refreshes_on_changes(self, poller: CanIEmailSyncPoller) -> None:
        report = SyncReport(new_properties=3, updated_levels=2, dry_run=False)
        poller._refresh_graph = AsyncMock()  # type: ignore[method-assign]

        await poller.store(report)

        poller._refresh_graph.assert_awaited_once()

    @pytest.mark.anyio()
    async def test_no_refresh_on_dry_run(self, poller: CanIEmailSyncPoller) -> None:
        report = SyncReport(new_properties=3, dry_run=True)
        poller._refresh_graph = AsyncMock()  # type: ignore[method-assign]

        await poller.store(report)

        poller._refresh_graph.assert_not_awaited()

    @pytest.mark.anyio()
    async def test_no_refresh_when_no_changes(self, poller: CanIEmailSyncPoller) -> None:
        report = SyncReport(dry_run=False)
        poller._refresh_graph = AsyncMock()  # type: ignore[method-assign]

        await poller.store(report)

        poller._refresh_graph.assert_not_awaited()

    @pytest.mark.anyio()
    async def test_store_none_is_noop(self, poller: CanIEmailSyncPoller) -> None:
        await poller.store(None)
        # Should not raise
