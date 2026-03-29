"""Track eval pass rate improvements over time.

Appends structured entries to traces/improvement_log.jsonl after each
11.22.x subtask to measure progress from 16.7% baseline toward 99%+.

CLI: python -m app.ai.agents.evals.improvement_tracker \
       --change "11.22.8 agent redefinition" \
       --agent scaffolder \
       --criterion mso_conditional_correctness \
       --before 0.0 --after 0.99 \
       --task-id 11.22.8
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

IMPROVEMENT_LOG = Path("traces/improvement_log.jsonl")


class ImprovementEntry(BaseModel):
    """Single improvement measurement."""

    date: str = Field(description="ISO date")
    change_description: str
    agent: str
    criterion: str
    before_rate: float
    after_rate: float
    delta: float
    task_id: str = Field(description="e.g. '11.22.8'")


def record_improvement(
    change_description: str,
    agent: str,
    criterion: str,
    before_rate: float,
    after_rate: float,
    task_id: str,
) -> ImprovementEntry:
    """Append an improvement entry to the log."""
    entry = ImprovementEntry(
        date=datetime.now(UTC).isoformat(),
        change_description=change_description,
        agent=agent,
        criterion=criterion,
        before_rate=before_rate,
        after_rate=after_rate,
        delta=after_rate - before_rate,
        task_id=task_id,
    )
    IMPROVEMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    tmp = IMPROVEMENT_LOG.with_suffix(".jsonl.tmp")
    line = entry.model_dump_json() + "\n"
    # Atomic append: write to temp file, then append to log
    tmp.write_text(line)
    with IMPROVEMENT_LOG.open("a") as f:
        f.write(line)
    tmp.unlink(missing_ok=True)
    logger.info("eval.improvement_recorded", extra={"entry": entry.model_dump()})
    return entry


def load_improvements(log_path: Path | None = None) -> list[ImprovementEntry]:
    """Load all improvement entries."""
    path = log_path or IMPROVEMENT_LOG
    if not path.exists():
        return []
    entries: list[ImprovementEntry] = []
    for line in path.read_text().strip().split("\n"):
        if line:
            entries.append(ImprovementEntry.model_validate_json(line))
    return entries


def summarise_progress(log_path: Path | None = None) -> dict[str, object]:
    """Summarise improvement log: latest rates per agent+criterion."""
    entries = load_improvements(log_path)
    if not entries:
        return {"entries": 0, "latest": {}}

    latest: dict[str, dict[str, float]] = {}
    for entry in entries:
        latest.setdefault(entry.agent, {})[entry.criterion] = entry.after_rate

    return {"entries": len(entries), "latest": latest}


def main() -> None:
    """CLI entry point for recording improvements."""
    parser = argparse.ArgumentParser(description="Record eval improvement")
    parser.add_argument("--change", required=True, help="Description of change")
    parser.add_argument("--agent", required=True, help="Agent name")
    parser.add_argument("--criterion", required=True, help="Criterion name")
    parser.add_argument("--before", type=float, required=True, help="Before pass rate")
    parser.add_argument("--after", type=float, required=True, help="After pass rate")
    parser.add_argument("--task-id", required=True, help="Task ID (e.g. 11.22.8)")
    args = parser.parse_args()

    entry = record_improvement(
        change_description=args.change,
        agent=args.agent,
        criterion=args.criterion,
        before_rate=args.before,
        after_rate=args.after,
        task_id=args.task_id,
    )
    delta_sign = "+" if entry.delta >= 0 else ""
    logger.info(
        f"Recorded: {entry.agent}/{entry.criterion} "
        f"{entry.before_rate:.1%} -> {entry.after_rate:.1%} "
        f"({delta_sign}{entry.delta:.1%})"
    )


if __name__ == "__main__":
    main()
