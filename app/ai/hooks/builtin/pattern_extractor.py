"""Pattern extractor hook — recurring failure pattern detection (strict profile)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.ai.hooks.registry import HookContext, HookEvent, HookRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _on_post_pipeline(ctx: HookContext) -> dict[str, Any]:
    """Analyze node traces for recurring patterns."""
    traces = ctx.metadata.get("traces", [])

    error_agents: list[str] = []
    failed_contracts: list[str] = []

    for trace in traces:
        if not hasattr(trace, "agent_name"):
            continue
        if hasattr(trace, "error") and trace.error:
            error_agents.append(trace.agent_name)
        if hasattr(trace, "contract_passed") and trace.contract_passed is False:
            failed_contracts.append(trace.agent_name)

    patterns: dict[str, Any] = {}

    if error_agents:
        error_counts = Counter(error_agents)
        patterns["recurring_errors"] = dict(error_counts)
        logger.info(
            "hooks.pattern_extractor.errors_detected",
            extra={
                "run_id": ctx.run_id,
                "error_counts": dict(error_counts),
            },
        )

    if failed_contracts:
        contract_counts = Counter(failed_contracts)
        patterns["recurring_contract_failures"] = dict(contract_counts)
        logger.info(
            "hooks.pattern_extractor.contract_failures_detected",
            extra={
                "run_id": ctx.run_id,
                "contract_counts": dict(contract_counts),
            },
        )

    return patterns


def register(registry: HookRegistry) -> None:
    """Register pattern extractor hook."""
    registry.register(
        HookEvent.POST_PIPELINE,
        _on_post_pipeline,
        name="pattern_extractor",
        profile="strict",
    )
