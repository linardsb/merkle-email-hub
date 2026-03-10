"""Tests for CanIEmailSyncPoller."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.knowledge.ontology.sync.poller import CanIEmailSyncPoller
from app.knowledge.ontology.sync.schemas import SyncDiff, SyncState


@pytest.fixture()
def poller() -> CanIEmailSyncPoller:  # type: ignore[misc]
    with patch("app.knowledge.ontology.sync.poller.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.ontology_sync.interval_hours = 168
        settings.ontology_sync.github_repo = "hteumeuleu/caniemail"
        settings.ontology_sync.github_branch = "main"
        settings.ontology_sync.request_timeout_seconds = 10
        settings.ontology_sync.max_features_per_sync = 500
        settings.ontology_sync.github_token = ""
        settings.cognee.enabled = False

        with patch(
            "app.knowledge.ontology.sync.caniemail_client.get_settings",
            return_value=settings,
        ):
            yield CanIEmailSyncPoller()


class TestFetch:
    @pytest.mark.anyio()
    async def test_skips_unchanged_sha(self, poller: CanIEmailSyncPoller) -> None:
        poller._client = MagicMock()
        poller._client.get_latest_commit_sha = AsyncMock(return_value="abc123")
        poller._load_state = AsyncMock(  # type: ignore[method-assign]
            return_value=SyncState(last_commit_sha="abc123"),
        )

        result = await poller.fetch()
        assert result is None

    @pytest.mark.anyio()
    async def test_fetches_on_new_sha(self, poller: CanIEmailSyncPoller) -> None:
        poller._client = MagicMock()
        poller._client.get_latest_commit_sha = AsyncMock(return_value="new_sha")
        poller._client.fetch_all_features = AsyncMock(return_value=[])
        poller._load_state = AsyncMock(  # type: ignore[method-assign]
            return_value=SyncState(last_commit_sha="old_sha"),
        )

        result = await poller.fetch()
        assert result is not None
        assert result["sha"] == "new_sha"  # type: ignore[index]


class TestStore:
    @pytest.mark.anyio()
    async def test_applies_diff_when_changes(self, poller: CanIEmailSyncPoller) -> None:
        diff = SyncDiff(new_properties=["display_flex"])
        data = {"sha": "abc123", "features": [], "diff": diff}

        with (
            patch("app.knowledge.ontology.sync.poller.apply_sync", return_value=1) as mock_apply,
        ):
            poller._save_state = AsyncMock()  # type: ignore[method-assign]
            poller._refresh_graph = AsyncMock()  # type: ignore[method-assign]
            await poller.store(data)

        mock_apply.assert_called_once()
        poller._refresh_graph.assert_awaited_once()

    @pytest.mark.anyio()
    async def test_noop_when_no_changes(self, poller: CanIEmailSyncPoller) -> None:
        diff = SyncDiff()
        data = {"sha": "abc123", "features": [], "diff": diff}

        with patch("app.knowledge.ontology.sync.poller.apply_sync") as mock_apply:
            poller._save_state = AsyncMock()  # type: ignore[method-assign]
            poller._refresh_graph = AsyncMock()  # type: ignore[method-assign]
            await poller.store(data)

        mock_apply.assert_not_called()

    @pytest.mark.anyio()
    async def test_store_none_is_noop(self, poller: CanIEmailSyncPoller) -> None:
        await poller.store(None)
        # Should not raise
