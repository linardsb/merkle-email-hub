"""Context budget management for blueprint runs.

Implements three patterns from the Manus Agent Harness:
- Context compaction: full/compact result versions
- Trajectory summarization: compact JSON summary replacing verbose history
- Budget-triggered economy mode: degrade gracefully when tokens run low
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.blueprints.engine import BlueprintRun
    from app.ai.blueprints.protocols import AgentHandoff

__all__ = [
    "ECONOMY_MODE_THRESHOLD",
    "ContextBudget",
    "compact_handoff_history",
    "summarize_trajectory",
]

ECONOMY_MODE_THRESHOLD = 0.30


@dataclass(frozen=True)
class ContextBudget:
    """Per-section token limits for context assembly."""

    system_prompt_max: int = 4000
    skill_docs_max: int = 2000
    handoff_summary_max: int = 1000
    user_message_max: int = 4000
    total_max: int = 12000


def compact_handoff_history(
    history: list[AgentHandoff],
    *,
    economy: bool = False,
) -> list[AgentHandoff]:
    """Return compacted handoff history.

    Normal mode: compact all but the last entry (preserve latest at full fidelity).
    Economy mode: compact all entries.
    Empty/single lists returned as-is in normal mode.
    """
    if not history:
        return []

    if economy:
        return [h.compact() for h in history]

    if len(history) == 1:
        return list(history)

    return [h.compact() for h in history[:-1]] + [history[-1]]


def summarize_trajectory(run: BlueprintRun) -> str:
    """Build a single-line JSON summary of the run trajectory.

    Includes: passes completed, QA status, and retry attempt counts.
    """
    passes = [{"node": p.node_name, "status": p.status} for p in run.progress]

    retries = {node: count for node, count in run.iteration_counts.items() if count > 1}

    summary: dict[str, object] = {
        "passes": passes,
        "qa_passed": run.qa_passed,
    }
    if retries:
        summary["retries"] = retries

    return json.dumps(summary, separators=(",", ":"))
