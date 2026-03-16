"""Tests for blueprint resume from checkpoint (14.3)."""

from unittest.mock import AsyncMock

import pytest

from app.ai.blueprints.checkpoint import (
    CheckpointData,
    restore_run,
    serialize_run,
)
from app.ai.blueprints.engine import (
    BlueprintDefinition,
    BlueprintEngine,
    BlueprintRun,
    Edge,
)
from app.ai.blueprints.exceptions import BlueprintError
from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.ai.blueprints.schemas import BlueprintProgress

# ── Helpers ──


class _StubNode:
    """Minimal node for engine tests."""

    def __init__(self, name: str, html: str = "<p>done</p>") -> None:
        self._name = name
        self._html = html

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        return NodeResult(status="success", html=self._html)


def _three_node_definition() -> BlueprintDefinition:
    """Three-node blueprint: entry → middle → finish."""
    return BlueprintDefinition(
        name="test_bp",
        nodes={
            "entry": _StubNode("entry", "<p>step1</p>"),
            "middle": _StubNode("middle", "<p>step2</p>"),
            "finish": _StubNode("finish", "<p>final</p>"),
        },
        edges=[
            Edge(from_node="entry", to_node="middle", condition="success"),
            Edge(from_node="middle", to_node="finish", condition="success"),
        ],
        entry_node="entry",
    )


def _make_checkpoint(
    *,
    run_id: str = "run123",
    blueprint_name: str = "test_bp",
    node_name: str = "entry",
    next_node_name: str | None = "middle",
    status: str = "running",
    html: str = "<p>step1</p>",
) -> CheckpointData:
    """Create a CheckpointData for resume tests."""
    return CheckpointData(
        run_id=run_id,
        blueprint_name=blueprint_name,
        node_name=node_name,
        node_index=0,
        status=status,
        html=html,
        progress=[
            {
                "node_name": "entry",
                "node_type": "deterministic",
                "status": "success",
                "iteration": 0,
                "summary": "success",
                "duration_ms": 10.0,
            }
        ],
        iteration_counts={},
        qa_failures=[],
        qa_failure_details=[],
        qa_passed=None,
        model_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        skipped_nodes=[],
        routing_decisions=[],
        handoff_history=[],
        next_node_name=next_node_name,
    )


# ── Resume tests ──


class TestResumeFromCheckpoint:
    """BlueprintEngine.resume() tests."""

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self) -> None:
        """Resume starts execution from the next node, not entry."""
        mock_store = AsyncMock()
        mock_store.load_latest = AsyncMock(return_value=_make_checkpoint())
        mock_store.save = AsyncMock()

        engine = BlueprintEngine(_three_node_definition(), checkpoint_store=mock_store)
        run = await engine.resume(run_id="run123", brief="test")

        assert run.status == "completed"
        # Should have prior entry progress + middle + finish = 3 total
        assert len(run.progress) == 3
        assert run.progress[0].node_name == "entry"  # from checkpoint
        assert run.progress[1].node_name == "middle"  # executed
        assert run.progress[2].node_name == "finish"  # executed
        assert run.html == "<p>final</p>"

    @pytest.mark.asyncio
    async def test_resume_no_checkpoint_raises(self) -> None:
        """Resume with unknown run_id raises BlueprintError."""
        mock_store = AsyncMock()
        mock_store.load_latest = AsyncMock(return_value=None)

        engine = BlueprintEngine(_three_node_definition(), checkpoint_store=mock_store)
        with pytest.raises(BlueprintError, match="No checkpoint found"):
            await engine.resume(run_id="unknown", brief="test")

    @pytest.mark.asyncio
    async def test_resume_blueprint_mismatch_raises(self) -> None:
        """Checkpoint from different blueprint raises BlueprintError."""
        mock_store = AsyncMock()
        mock_store.load_latest = AsyncMock(return_value=_make_checkpoint(blueprint_name="other_bp"))

        engine = BlueprintEngine(_three_node_definition(), checkpoint_store=mock_store)
        with pytest.raises(BlueprintError, match="Blueprint mismatch"):
            await engine.resume(run_id="run123", brief="test")

    @pytest.mark.asyncio
    async def test_resume_terminal_checkpoint(self) -> None:
        """Checkpoint with next_node_name=None returns completed run."""
        mock_store = AsyncMock()
        mock_store.load_latest = AsyncMock(return_value=_make_checkpoint(next_node_name=None))

        engine = BlueprintEngine(_three_node_definition(), checkpoint_store=mock_store)
        run = await engine.resume(run_id="run123", brief="test")

        assert run.status == "completed"
        # Only the checkpoint's prior progress, no new execution
        assert len(run.progress) == 1
        assert run.progress[0].node_name == "entry"

    @pytest.mark.asyncio
    async def test_resume_missing_node_raises(self) -> None:
        """Checkpoint's next_node references a deleted node → error."""
        mock_store = AsyncMock()
        mock_store.load_latest = AsyncMock(
            return_value=_make_checkpoint(next_node_name="deleted_node")
        )

        engine = BlueprintEngine(_three_node_definition(), checkpoint_store=mock_store)
        with pytest.raises(BlueprintError, match="no longer exists"):
            await engine.resume(run_id="run123", brief="test")

    @pytest.mark.asyncio
    async def test_resume_checkpoints_disabled_raises(self) -> None:
        """Engine with no checkpoint_store cannot resume."""
        engine = BlueprintEngine(_three_node_definition(), checkpoint_store=None)
        with pytest.raises(BlueprintError, match="Checkpoints are not enabled"):
            await engine.resume(run_id="run123", brief="test")

    @pytest.mark.asyncio
    async def test_resume_preserves_prior_progress(self) -> None:
        """Progress entries from before the checkpoint are preserved."""
        mock_store = AsyncMock()
        mock_store.load_latest = AsyncMock(
            return_value=_make_checkpoint(
                node_name="middle",
                next_node_name="finish",
                html="<p>step2</p>",
            )
        )
        mock_store.save = AsyncMock()

        engine = BlueprintEngine(_three_node_definition(), checkpoint_store=mock_store)
        run = await engine.resume(run_id="run123", brief="test")

        # Prior progress (entry) + newly executed (finish)
        assert run.progress[0].node_name == "entry"
        assert run.progress[1].node_name == "finish"
        assert run.html == "<p>final</p>"

    @pytest.mark.asyncio
    async def test_resume_sets_resumed_from(self) -> None:
        """BlueprintRun.resumed_from is set to the checkpoint node name."""
        mock_store = AsyncMock()
        mock_store.load_latest = AsyncMock(return_value=_make_checkpoint())
        mock_store.save = AsyncMock()

        engine = BlueprintEngine(_three_node_definition(), checkpoint_store=mock_store)
        run = await engine.resume(run_id="run123", brief="test")

        assert run.resumed_from == "entry"


class TestCheckpointNextNode:
    """serialize_run() with next_node_name round-trips correctly."""

    def test_checkpoint_data_includes_next_node(self) -> None:
        run = BlueprintRun(run_id="test123", html="<p>test</p>")
        run.progress.append(
            BlueprintProgress(
                node_name="entry",
                node_type="deterministic",
                status="success",
                iteration=0,
                summary="ok",
                duration_ms=5.0,
            )
        )

        data = serialize_run(
            run,
            node_name="entry",
            node_index=0,
            blueprint_name="test_bp",
            next_node_name="middle",
        )
        assert data.next_node_name == "middle"

        # Round-trip via restore_run preserves run state
        restored = restore_run(data)
        assert restored.run_id == "test123"

    def test_checkpoint_data_next_node_none(self) -> None:
        run = BlueprintRun(run_id="test456")
        data = serialize_run(
            run,
            node_name="finish",
            node_index=2,
            blueprint_name="test_bp",
            next_node_name=None,
        )
        assert data.next_node_name is None


class TestResumeServiceLayer:
    """BlueprintService.resume() tests."""

    @pytest.mark.asyncio
    async def test_resume_service_db_none_raises(self) -> None:
        """Service.resume() without a DB session raises BlueprintError."""
        from app.ai.blueprints.schemas import BlueprintResumeRequest
        from app.ai.blueprints.service import BlueprintService

        svc = BlueprintService()
        req = BlueprintResumeRequest(run_id="run123", blueprint_name="campaign", brief="test")
        with pytest.raises(BlueprintError, match="Database session required"):
            await svc.resume(req, user_id=1, db=None)


class TestResumeRoute:
    """Route-level test for POST /resume endpoint."""

    @pytest.mark.asyncio
    async def test_resume_route_viewer_denied(self) -> None:
        """Viewer role gets 403 on POST /resume."""
        from unittest.mock import MagicMock

        from httpx import ASGITransport, AsyncClient

        from app.auth.dependencies import get_current_user
        from app.core.database import get_db
        from app.core.rate_limit import limiter
        from app.main import app

        limiter.enabled = False

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "viewer"

        mock_db = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/blueprints/resume",
                    json={
                        "run_id": "run123",
                        "blueprint_name": "campaign",
                        "brief": "test",
                    },
                )

            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            limiter.enabled = True

    @pytest.mark.asyncio
    async def test_resume_route_valid_resume(self) -> None:
        """Admin/developer can successfully resume a run."""
        from unittest.mock import MagicMock, patch

        from httpx import ASGITransport, AsyncClient

        from app.auth.dependencies import get_current_user
        from app.core.database import get_db
        from app.core.rate_limit import limiter
        from app.main import app

        limiter.enabled = False

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "developer"

        mock_db = AsyncMock()

        from app.ai.blueprints.schemas import BlueprintRunResponse

        mock_response = BlueprintRunResponse(
            run_id="run123",
            blueprint_name="campaign",
            status="completed",
            html="<p>resumed</p>",
            progress=[],
            checkpoint_count=2,
            resumed_from="scaffolder",
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with patch("app.ai.blueprints.routes.get_blueprint_service") as mock_get_svc:
                mock_svc = AsyncMock()
                mock_svc.resume = AsyncMock(return_value=mock_response)
                mock_get_svc.return_value = mock_svc

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    resp = await client.post(
                        "/api/v1/blueprints/resume",
                        json={
                            "run_id": "run123",
                            "blueprint_name": "campaign",
                            "brief": "test brief",
                        },
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert data["run_id"] == "run123"
            assert data["resumed_from"] == "scaffolder"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            limiter.enabled = True

    @pytest.mark.asyncio
    async def test_resume_route_invalid_run_id(self) -> None:
        """Resume with unknown run_id returns error from service."""
        from unittest.mock import MagicMock, patch

        from httpx import ASGITransport, AsyncClient

        from app.auth.dependencies import get_current_user
        from app.core.database import get_db
        from app.core.rate_limit import limiter
        from app.main import app

        limiter.enabled = False

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "admin"

        mock_db = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with patch("app.ai.blueprints.routes.get_blueprint_service") as mock_get_svc:
                mock_svc = AsyncMock()
                mock_svc.resume = AsyncMock(
                    side_effect=BlueprintError("No checkpoint found for run unknown")
                )
                mock_get_svc.return_value = mock_svc

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    resp = await client.post(
                        "/api/v1/blueprints/resume",
                        json={
                            "run_id": "unknown",
                            "blueprint_name": "campaign",
                            "brief": "test",
                        },
                    )

            assert resp.status_code in (400, 422, 500)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            limiter.enabled = True

    @pytest.mark.asyncio
    async def test_resume_route_unauthenticated(self) -> None:
        """Unauthenticated request returns 401/403."""
        from httpx import ASGITransport, AsyncClient

        from app.core.rate_limit import limiter
        from app.main import app

        limiter.enabled = False

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/v1/blueprints/resume",
                    json={
                        "run_id": "run123",
                        "blueprint_name": "campaign",
                        "brief": "test",
                    },
                )

            assert resp.status_code in (401, 403)
        finally:
            limiter.enabled = True
