"""Tests for checkpoint cleanup, poller, route, and response fields (14.5)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.blueprints.checkpoint_cleanup import (
    CheckpointCleanupPoller,
    cleanup_completed_runs,
    cleanup_old_checkpoints,
)
from app.ai.blueprints.schemas import BlueprintRunResponse

# ── Cleanup function tests ──


class TestCleanupOldCheckpoints:
    """cleanup_old_checkpoints() deletes rows older than max_age_days."""

    @pytest.mark.asyncio
    async def test_deletes_checkpoints_older_than_max_age(self) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 5
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        count = await cleanup_old_checkpoints(db, max_age_days=7)

        assert count == 5
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_retains_checkpoints_within_max_age(self) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 0
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        count = await cleanup_old_checkpoints(db, max_age_days=30)

        assert count == 0

    @pytest.mark.asyncio
    async def test_zero_max_age_deletes_all(self) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 42
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        count = await cleanup_old_checkpoints(db, max_age_days=0)

        assert count == 42


class TestCleanupCompletedRuns:
    """cleanup_completed_runs() deletes checkpoints for completed runs."""

    @pytest.mark.asyncio
    async def test_deletes_checkpoints_for_completed_runs(self) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 10
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        count = await cleanup_completed_runs(db)

        assert count == 10
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_retains_checkpoints_for_running_runs(self) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 0
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        count = await cleanup_completed_runs(db)

        assert count == 0


# ── Poller tests ──


class TestCheckpointCleanupPoller:
    """CheckpointCleanupPoller configuration and behaviour."""

    def test_poller_config(self) -> None:
        poller = CheckpointCleanupPoller()
        assert poller.name == "checkpoint-cleanup"
        assert poller.interval_seconds == 86400

    @pytest.mark.asyncio
    async def test_fetch_calls_both_cleanup_functions(self) -> None:
        poller = CheckpointCleanupPoller()

        with (
            patch(
                "app.ai.blueprints.checkpoint_cleanup.cleanup_old_checkpoints",
                new_callable=AsyncMock,
                return_value=3,
            ) as mock_old,
            patch(
                "app.ai.blueprints.checkpoint_cleanup.cleanup_completed_runs",
                new_callable=AsyncMock,
                return_value=2,
            ) as mock_completed,
            patch(
                "app.ai.blueprints.checkpoint_cleanup.get_db_context",
            ) as mock_ctx,
        ):
            mock_db = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await poller.fetch()

            mock_old.assert_called_once()
            mock_completed.assert_called_once()
            assert result == {"age_deleted": 3, "completed_deleted": 2}


# ── Route tests ──


class TestListRunCheckpointsRoute:
    """GET /runs/{run_id}/checkpoints endpoint."""

    @pytest.mark.asyncio
    async def test_list_checkpoints_empty_run(self) -> None:
        """Unknown run_id returns empty list."""
        from app.auth.dependencies import get_current_user
        from app.core.rate_limit import limiter
        from app.core.scoped_db import get_scoped_db
        from app.main import app

        limiter.enabled = False

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "admin"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_scoped_db] = lambda: mock_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/blueprints/runs/unknown-run/checkpoints")

            assert resp.status_code == 200
            data = resp.json()
            assert data["run_id"] == "unknown-run"
            assert data["checkpoints"] == []
            assert data["count"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_scoped_db, None)
            limiter.enabled = True

    @pytest.mark.asyncio
    async def test_list_checkpoints_success(self) -> None:
        """Returns checkpoint list with correct fields."""
        from app.auth.dependencies import get_current_user
        from app.core.rate_limit import limiter
        from app.core.scoped_db import get_scoped_db
        from app.main import app

        limiter.enabled = False

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "admin"

        now = datetime.now(UTC)
        mock_row = MagicMock()
        mock_row.node_name = "scaffolder"
        mock_row.node_index = 0
        mock_row.state_json = {"status": "completed"}
        mock_row.html_hash = "abc123"
        mock_row.created_at = now

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_row]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_scoped_db] = lambda: mock_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/blueprints/runs/run-123/checkpoints")

            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] == 1
            cp = data["checkpoints"][0]
            assert cp["node_name"] == "scaffolder"
            assert cp["node_index"] == 0
            assert cp["status"] == "completed"
            assert cp["html_hash"] == "abc123"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_scoped_db, None)
            limiter.enabled = True

    @pytest.mark.asyncio
    async def test_list_checkpoints_viewer_denied(self) -> None:
        """Viewer role gets 403."""
        from app.auth.dependencies import get_current_user
        from app.core.rate_limit import limiter
        from app.core.scoped_db import get_scoped_db
        from app.main import app

        limiter.enabled = False

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "viewer"

        mock_db = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_scoped_db] = lambda: mock_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/blueprints/runs/run-123/checkpoints")

            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_scoped_db, None)
            limiter.enabled = True


# ── Response schema tests ──


class TestBlueprintRunResponseCheckpointFields:
    """BlueprintRunResponse includes checkpoint_count and resumed_from."""

    def test_response_includes_checkpoint_count(self) -> None:
        resp = BlueprintRunResponse(
            run_id="r1",
            blueprint_name="campaign",
            status="completed",
            html="<p>ok</p>",
            progress=[],
        )
        assert resp.checkpoint_count == 0

    def test_response_includes_resumed_from(self) -> None:
        resp = BlueprintRunResponse(
            run_id="r1",
            blueprint_name="campaign",
            status="completed",
            html="<p>ok</p>",
            progress=[],
        )
        assert resp.resumed_from is None

    def test_response_with_custom_values(self) -> None:
        resp = BlueprintRunResponse(
            run_id="r1",
            blueprint_name="campaign",
            status="completed",
            html="<p>ok</p>",
            progress=[],
            checkpoint_count=5,
            resumed_from="node-2",
        )
        assert resp.checkpoint_count == 5
        assert resp.resumed_from == "node-2"
