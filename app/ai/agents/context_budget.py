"""Context budget management for blueprint runs.

Implements three patterns from the Manus Agent Harness:
- Context compaction: full/compact result versions
- Trajectory summarization: compact JSON summary replacing verbose history
- Budget-triggered economy mode: degrade gracefully when tokens run low

Phase 2: Per-agent budgets with tuned values.
Phase 3: Decaying resolution handoff history (3-tier: full/compact/summary).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.blueprints.engine import BlueprintRun
    from app.ai.blueprints.protocols import AgentHandoff

__all__ = [
    "AGENT_BUDGETS",
    "ECONOMY_MODE_THRESHOLD",
    "ContextBudget",
    "compact_handoff_history",
    "get_budget",
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


# Per-agent budgets tuned to each agent's needs.
# Scaffolder needs rich context (brief + template + design system).
# Dark Mode primarily needs <style> blocks.
# Content needs brief + brand voice.
# Other agents fall between.
AGENT_BUDGETS: dict[str, ContextBudget] = {
    "scaffolder": ContextBudget(
        system_prompt_max=5000,
        skill_docs_max=3000,
        handoff_summary_max=1500,
        user_message_max=6000,
        total_max=16000,
    ),
    "dark_mode": ContextBudget(
        system_prompt_max=3000,
        skill_docs_max=1500,
        handoff_summary_max=500,
        user_message_max=3000,
        total_max=8000,
    ),
    "content": ContextBudget(
        system_prompt_max=3500,
        skill_docs_max=2000,
        handoff_summary_max=800,
        user_message_max=3500,
        total_max=10000,
    ),
    "accessibility": ContextBudget(
        system_prompt_max=3500,
        skill_docs_max=2000,
        handoff_summary_max=800,
        user_message_max=3500,
        total_max=10000,
    ),
    "outlook_fixer": ContextBudget(
        system_prompt_max=4000,
        skill_docs_max=2500,
        handoff_summary_max=800,
        user_message_max=4000,
        total_max=12000,
    ),
    "personalisation": ContextBudget(
        system_prompt_max=3500,
        skill_docs_max=2000,
        handoff_summary_max=800,
        user_message_max=3500,
        total_max=10000,
    ),
    "code_reviewer": ContextBudget(
        system_prompt_max=3500,
        skill_docs_max=2000,
        handoff_summary_max=800,
        user_message_max=3500,
        total_max=10000,
    ),
    "knowledge": ContextBudget(
        system_prompt_max=4000,
        skill_docs_max=2500,
        handoff_summary_max=500,
        user_message_max=5000,
        total_max=12000,
    ),
    "innovation": ContextBudget(
        system_prompt_max=3500,
        skill_docs_max=2000,
        handoff_summary_max=800,
        user_message_max=3500,
        total_max=10000,
    ),
}

_DEFAULT_BUDGET = ContextBudget()


def get_budget(agent_name: str) -> ContextBudget:
    """Get the context budget for a specific agent, falling back to default."""
    return AGENT_BUDGETS.get(agent_name, _DEFAULT_BUDGET)


def compact_handoff_history(
    history: list[AgentHandoff],
    *,
    economy: bool = False,
    decay_tiers: bool = False,
) -> list[AgentHandoff | str]:
    """Return compacted handoff history.

    Normal mode: compact all but the last entry (preserve latest at full fidelity).
    Economy mode: compact all entries.
    Decay tiers (Phase 3): 3-tier resolution when history is long:
      - Latest: full fidelity
      - Previous 2: compact (artifact stripped)
      - Older: single-line summary string

    Empty/single lists returned as-is in normal mode.
    """
    if not history:
        return []

    if economy:
        out: list[AgentHandoff | str] = [h.compact() for h in history]
        return out

    if decay_tiers and len(history) >= 4:
        result: list[AgentHandoff | str] = []
        # Older entries: summary strings
        for h in history[:-3]:
            result.append(h.summary())
        # Previous 2: compact
        for h in history[-3:-1]:
            result.append(h.compact())
        # Latest: full
        result.append(history[-1])
        return result

    if len(history) == 1:
        single: list[AgentHandoff | str] = list(history)
        return single

    compacted: list[AgentHandoff | str] = [h.compact() for h in history[:-1]]
    compacted.append(history[-1])
    return compacted


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
