"""Structured logger hook — emits JSON events for all pipeline events (standard profile)."""

from __future__ import annotations

from app.ai.hooks.registry import HookContext, HookEvent, HookRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _on_event(ctx: HookContext) -> None:
    """Emit a structured log entry for any pipeline event."""
    logger.info(
        f"hooks.structured_logger.{ctx.event}",
        extra={
            "run_id": ctx.run_id,
            "pipeline_name": ctx.pipeline_name,
            "event": str(ctx.event),
            "agent_name": ctx.agent_name,
            "level": ctx.level,
            "cost_tokens": ctx.cost_tokens,
        },
    )


def register(registry: HookRegistry) -> None:
    """Register structured logger hooks for all events."""
    for event in HookEvent:
        registry.register(
            event,
            _on_event,
            name=f"structured_logger_{event}",
            profile="standard",
        )
