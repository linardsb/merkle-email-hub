"""Automatic cleanup of old blueprint checkpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.blueprints.checkpoint_models import BlueprintCheckpoint
from app.core.config import get_settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.core.poller import DataPoller

logger = get_logger(__name__)
settings = get_settings()


async def cleanup_old_checkpoints(db: AsyncSession, max_age_days: int = 7) -> int:
    """Delete checkpoints older than max_age_days. Returns count deleted."""
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    stmt = delete(BlueprintCheckpoint).where(BlueprintCheckpoint.created_at < cutoff)
    result = await db.execute(stmt)
    await db.commit()
    count: int = result.rowcount  # type: ignore[attr-defined]
    logger.info(
        "blueprint.checkpoint_cleanup",
        extra={"deleted_count": count, "max_age_days": max_age_days},
    )
    return count


async def cleanup_completed_runs(db: AsyncSession) -> int:
    """Delete all checkpoints for runs whose latest checkpoint has status 'completed'.

    Completed runs don't need checkpoints (no resume needed).
    Returns count deleted.
    """
    # Find run_ids where the latest checkpoint (by node_index) has status='completed'
    latest_per_run = (
        select(
            BlueprintCheckpoint.run_id,
            func.max(BlueprintCheckpoint.node_index).label("max_idx"),
        )
        .group_by(BlueprintCheckpoint.run_id)
        .subquery()
    )
    completed_runs = (
        select(BlueprintCheckpoint.run_id)
        .join(
            latest_per_run,
            (BlueprintCheckpoint.run_id == latest_per_run.c.run_id)
            & (BlueprintCheckpoint.node_index == latest_per_run.c.max_idx),
        )
        .where(
            BlueprintCheckpoint.state_json["status"].astext == "completed"  # pyright: ignore[reportIndexIssue]
        )
    )
    stmt = delete(BlueprintCheckpoint).where(BlueprintCheckpoint.run_id.in_(completed_runs))
    result = await db.execute(stmt)
    await db.commit()
    count: int = result.rowcount  # type: ignore[attr-defined]
    logger.info(
        "blueprint.checkpoint_cleanup_completed_runs",
        extra={"deleted_count": count},
    )
    return count


class CheckpointCleanupPoller(DataPoller):
    """Daily cleanup of old/completed blueprint checkpoints."""

    def __init__(self) -> None:
        super().__init__(
            name="checkpoint-cleanup",
            interval_seconds=86400,  # 24 hours
        )

    async def fetch(self) -> object:
        """Run cleanup cycle."""
        retention_days = settings.blueprint.checkpoint_retention_days
        async with get_db_context() as db:
            age_deleted = await cleanup_old_checkpoints(db, max_age_days=retention_days)
            completed_deleted = await cleanup_completed_runs(db)
            return {"age_deleted": age_deleted, "completed_deleted": completed_deleted}

    async def store(self, data: object) -> None:
        """Log cleanup results."""
        logger.info("blueprint.checkpoint_cleanup_cycle_completed", extra={"stats": str(data)})
