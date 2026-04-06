"""Cost tracker hook — accumulates per-agent token usage (minimal profile)."""

from __future__ import annotations

import time
from typing import Any

from app.ai.hooks.registry import HookContext, HookEvent, HookRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level accumulator, keyed by run_id.
# Entries have a monotonic timestamp for TTL-based eviction to prevent leaks
# if POST_PIPELINE never fires (pipeline crash).
_run_totals: dict[str, dict[str, int]] = {}
_run_timestamps: dict[str, float] = {}
_EVICTION_TTL_S = 3600  # 1 hour


def _evict_stale() -> None:
    """Remove entries older than TTL to prevent unbounded growth."""
    now = time.monotonic()
    stale = [rid for rid, ts in _run_timestamps.items() if now - ts > _EVICTION_TTL_S]
    for rid in stale:
        _run_totals.pop(rid, None)
        _run_timestamps.pop(rid, None)


async def _on_post_agent(ctx: HookContext) -> dict[str, Any]:
    """Accumulate token count for an agent."""
    agent = ctx.agent_name or "unknown"
    _run_timestamps.setdefault(ctx.run_id, time.monotonic())
    totals = _run_totals.setdefault(ctx.run_id, {})
    totals[agent] = totals.get(agent, 0) + ctx.cost_tokens
    return {"agent": agent, "tokens": ctx.cost_tokens}


async def _on_post_pipeline(ctx: HookContext) -> dict[str, Any]:
    """Log total and per-agent token breakdown."""
    totals = _run_totals.pop(ctx.run_id, {})
    _run_timestamps.pop(ctx.run_id, None)
    grand_total = sum(totals.values())
    logger.info(
        "hooks.cost_tracker.summary",
        extra={
            "run_id": ctx.run_id,
            "total_tokens": grand_total,
            "by_agent": totals,
        },
    )
    # Evict stale entries from runs that crashed before POST_PIPELINE
    _evict_stale()
    return {"total_tokens": grand_total, "by_agent": totals}


def register(registry: HookRegistry) -> None:
    """Register cost tracker hooks."""
    registry.register(
        HookEvent.POST_AGENT,
        _on_post_agent,
        name="cost_tracker",
        profile="minimal",
    )
    registry.register(
        HookEvent.POST_PIPELINE,
        _on_post_pipeline,
        name="cost_tracker_summary",
        profile="minimal",
    )
