"""Progress reporter hook — updates ProgressTracker (standard profile)."""

from __future__ import annotations

from app.ai.hooks.registry import HookContext, HookEvent, HookRegistry
from app.core.logging import get_logger
from app.core.progress import OperationStatus, ProgressTracker

logger = get_logger(__name__)


async def _on_pre_pipeline(ctx: HookContext) -> None:
    """Start progress tracking for the pipeline run."""
    ProgressTracker.start(ctx.run_id, "pipeline")


async def _on_post_level(ctx: HookContext) -> None:
    """Update progress based on level completion."""
    total_levels = ctx.metadata.get("total_levels", 1)
    current_level = (ctx.level or 0) + 1
    progress = min(int((current_level / total_levels) * 100), 99)
    ProgressTracker.update(ctx.run_id, progress=progress)


async def _on_post_pipeline(ctx: HookContext) -> None:
    """Mark pipeline as completed."""
    has_errors = any(t.error for t in ctx.metadata.get("traces", []) if hasattr(t, "error"))
    if has_errors:
        ProgressTracker.update(
            ctx.run_id,
            progress=100,
            status=OperationStatus.FAILED,
        )
    else:
        ProgressTracker.update(
            ctx.run_id,
            progress=100,
            status=OperationStatus.COMPLETED,
        )


def register(registry: HookRegistry) -> None:
    """Register progress reporter hooks."""
    registry.register(
        HookEvent.PRE_PIPELINE,
        _on_pre_pipeline,
        name="progress_reporter_start",
        profile="standard",
    )
    registry.register(
        HookEvent.POST_LEVEL,
        _on_post_level,
        name="progress_reporter_level",
        profile="standard",
    )
    registry.register(
        HookEvent.POST_PIPELINE,
        _on_post_pipeline,
        name="progress_reporter_complete",
        profile="standard",
    )
