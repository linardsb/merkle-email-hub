"""Checkpoint storage for blueprint run state persistence."""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.ai.blueprints.engine import BlueprintRun

from app.ai.blueprints.checkpoint_models import BlueprintCheckpoint
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CheckpointData:
    """Immutable snapshot of blueprint run state at a given node."""

    run_id: str
    blueprint_name: str
    node_name: str
    node_index: int
    status: str
    html: str
    progress: list[dict[str, Any]]
    iteration_counts: dict[str, int]
    qa_failures: list[str]
    qa_failure_details: list[dict[str, Any]]
    qa_passed: bool | None
    model_usage: dict[str, int]
    skipped_nodes: list[str]
    routing_decisions: list[dict[str, Any]]
    handoff_history: list[dict[str, Any]]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class CheckpointStore(Protocol):
    """Protocol for checkpoint persistence backends."""

    async def save(self, data: CheckpointData) -> None:
        """Persist a checkpoint."""
        ...

    async def load_latest(self, run_id: str) -> CheckpointData | None:
        """Load the most recent checkpoint for a run."""
        ...

    async def list_checkpoints(self, run_id: str) -> list[CheckpointData]:
        """List all checkpoints for a run, ordered by node_index."""
        ...

    async def delete_run(self, run_id: str) -> int:
        """Delete all checkpoints for a run. Returns count deleted."""
        ...


class PostgresCheckpointStore:
    """PostgreSQL-backed checkpoint store."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, data: CheckpointData) -> None:
        """Persist a checkpoint to PostgreSQL."""
        start = time.monotonic()
        state = _checkpoint_to_dict(data)
        html_hash = hashlib.sha256(data.html.encode()).hexdigest()

        row = BlueprintCheckpoint(
            run_id=data.run_id,
            blueprint_name=data.blueprint_name,
            node_name=data.node_name,
            node_index=data.node_index,
            state_json=state,
            html_hash=html_hash,
        )
        self._db.add(row)
        await self._db.commit()
        elapsed_ms = (time.monotonic() - start) * 1000
        size_bytes = len(data.html.encode())
        logger.info(
            "checkpoint.save_completed",
            extra={
                "run_id": data.run_id,
                "node_name": data.node_name,
                "node_index": data.node_index,
                "size_bytes": size_bytes,
                "duration_ms": round(elapsed_ms, 1),
            },
        )

    async def load_latest(self, run_id: str) -> CheckpointData | None:
        """Load the most recent checkpoint for a run."""
        stmt = (
            select(BlueprintCheckpoint)
            .where(BlueprintCheckpoint.run_id == run_id)
            .order_by(BlueprintCheckpoint.node_index.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        age_seconds = (datetime.now(UTC) - row.created_at).total_seconds()
        logger.info(
            "checkpoint.loaded",
            extra={
                "run_id": run_id,
                "node_name": row.node_name,
                "age_seconds": round(age_seconds, 1),
            },
        )
        return _dict_to_checkpoint(row.state_json)

    async def list_checkpoints(self, run_id: str) -> list[CheckpointData]:
        """List all checkpoints for a run, ordered by node_index ascending."""
        stmt = (
            select(BlueprintCheckpoint)
            .where(BlueprintCheckpoint.run_id == run_id)
            .order_by(BlueprintCheckpoint.node_index.asc())
        )
        result = await self._db.execute(stmt)
        return [_dict_to_checkpoint(row.state_json) for row in result.scalars().all()]

    async def delete_run(self, run_id: str) -> int:
        """Delete all checkpoints for a run."""
        stmt = delete(BlueprintCheckpoint).where(BlueprintCheckpoint.run_id == run_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        count: int = result.rowcount  # type: ignore[attr-defined]
        logger.info(
            "checkpoint.delete_completed",
            extra={"run_id": run_id, "deleted_count": count},
        )
        return count


# ── Serialization helpers ──


def serialize_run(
    run: BlueprintRun,
    node_name: str,
    node_index: int,
    blueprint_name: str,
) -> CheckpointData:
    """Snapshot current BlueprintRun state into a CheckpointData.

    Converts frozen dataclass fields (tuples of dataclasses) to plain dicts
    for JSON-safe storage.

    Import of BlueprintRun is deferred via ``from __future__ import annotations``
    to avoid circular imports (engine.py → checkpoint.py → engine.py).
    """
    return CheckpointData(
        run_id=run.run_id,
        blueprint_name=blueprint_name,
        node_name=node_name,
        node_index=node_index,
        status=run.status,
        html=run.html,
        progress=[p.model_dump() for p in run.progress],
        iteration_counts=dict(run.iteration_counts),
        qa_failures=list(run.qa_failures),
        qa_failure_details=[
            {
                "check_name": f.check_name,
                "score": f.score,
                "details": f.details,
                "suggested_agent": f.suggested_agent,
                "priority": f.priority,
                "severity": f.severity,
            }
            for f in run.qa_failure_details
        ],
        qa_passed=run.qa_passed,
        model_usage=dict(run.model_usage),
        skipped_nodes=list(run.skipped_nodes),
        routing_decisions=[
            {
                "node_name": rd.node_name,
                "action": str(rd.action),
                "reason": rd.reason,
            }
            for rd in run.routing_decisions
        ],
        handoff_history=[
            {
                "agent_name": h.agent_name,
                "status": str(h.status),
                "decisions": list(h.decisions),
                "warnings": list(h.warnings),
                "component_refs": list(h.component_refs),
                "confidence": h.confidence,
            }
            for h in run._handoff_history
        ],
    )


def restore_run(data: CheckpointData) -> BlueprintRun:
    """Reconstruct a BlueprintRun from a CheckpointData snapshot.

    Re-creates typed fields (BlueprintProgress, StructuredFailure, etc.)
    from plain dicts.
    """
    from app.ai.blueprints.engine import BlueprintRun
    from app.ai.blueprints.protocols import AgentHandoff, StructuredFailure
    from app.ai.blueprints.route_advisor import RoutingAction, RoutingDecision
    from app.ai.blueprints.schemas import BlueprintProgress

    progress = [BlueprintProgress(**p) for p in data.progress]

    qa_failure_details = [StructuredFailure(**f) for f in data.qa_failure_details]

    routing_decisions = tuple(
        RoutingDecision(
            node_name=rd["node_name"],
            action=RoutingAction(rd["action"]),
            reason=rd["reason"],
        )
        for rd in data.routing_decisions
    )

    handoff_history = [
        AgentHandoff(
            agent_name=h["agent_name"],
            status=h.get("status", "ok"),
            decisions=tuple(h.get("decisions", ())),
            warnings=tuple(h.get("warnings", ())),
            component_refs=tuple(h.get("component_refs", ())),
            confidence=h.get("confidence"),
        )
        for h in data.handoff_history
    ]

    run = BlueprintRun(
        run_id=data.run_id,
        status=data.status,
        html=data.html,
        progress=progress,
        iteration_counts=dict(data.iteration_counts),
        qa_failures=list(data.qa_failures),
        qa_failure_details=qa_failure_details,
        qa_passed=data.qa_passed,
        model_usage=dict(data.model_usage),
        skipped_nodes=list(data.skipped_nodes),
        routing_decisions=routing_decisions,
    )
    run._handoff_history = handoff_history
    return run


# ── Internal helpers ──


def _checkpoint_to_dict(data: CheckpointData) -> dict[str, Any]:
    """Convert CheckpointData to a JSON-safe dict for JSONB storage."""
    d = asdict(data)
    d["created_at"] = data.created_at.isoformat()
    return d


def _dict_to_checkpoint(d: dict[str, Any]) -> CheckpointData:
    """Reconstruct CheckpointData from a JSONB dict."""
    d = dict(d)  # shallow copy
    created_str = d.pop("created_at", None)
    created_at = datetime.fromisoformat(created_str) if created_str else datetime.now(UTC)
    return CheckpointData(**d, created_at=created_at)
