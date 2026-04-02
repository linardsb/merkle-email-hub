"""Auto-generate regression YAML from failed adversarial verdicts.

When an adversarial case fails, it becomes a permanent regression test case
to ensure the failure mode is tracked and eventually fixed.

CLI: python -m app.ai.agents.evals.adversarial_regression \
       --verdicts traces/ --output app/ai/agents/evals/test_cases/regression/
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_failures(verdicts_dir: Path) -> list[dict[str, Any]]:
    """Load adversarial verdicts and return only failed cases."""
    failures: list[dict[str, Any]] = []
    for vfile in sorted(verdicts_dir.glob("*_adversarial_verdicts.jsonl")):
        with vfile.open() as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                verdict = json.loads(stripped)
                if verdict.get("error"):
                    continue
                if not verdict.get("overall_pass", True):
                    failures.append(verdict)
    return failures


def generate_regression_entry(verdict: dict[str, Any]) -> dict[str, Any]:
    """Convert a failed adversarial verdict into a regression YAML entry."""
    failed_criteria = [
        cr["criterion"] for cr in verdict.get("criteria_results", []) if not cr.get("passed", True)
    ]

    # Extract attack_type from trace dimensions if available
    dimensions = verdict.get("dimensions", {})
    attack_type = dimensions.get("attack_type", "unknown")

    return {
        "name": verdict.get("trace_id", "unknown"),
        "agent": verdict.get("agent", "unknown"),
        "source": "adversarial",
        "attack_type": attack_type,
        "failed_criteria": failed_criteria,
        "date_added": datetime.now(UTC).strftime("%Y-%m-%d"),
    }


def write_regression_yaml(entries: list[dict[str, Any]], output_dir: Path) -> dict[str, int]:
    """Write regression entries grouped by agent to YAML files.

    Returns dict of {agent: count} for entries written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    by_agent: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        agent = entry["agent"]
        by_agent.setdefault(agent, []).append(entry)

    counts: dict[str, int] = {}
    for agent, agent_entries in sorted(by_agent.items()):
        output_file = output_dir / f"{agent}_adversarial.yaml"

        # Load existing entries to avoid duplicates
        existing: list[dict[str, Any]] = []
        existing_names: set[str] = set()
        if output_file.exists():
            with output_file.open() as f:
                loaded: list[dict[str, Any]] = yaml.safe_load(f) or []
            existing = loaded
            existing_names = {e["name"] for e in existing}

        new_entries = [e for e in agent_entries if e["name"] not in existing_names]
        if not new_entries:
            continue

        combined: list[dict[str, Any]] = existing + new_entries
        with output_file.open("w") as f:
            yaml.dump(combined, f, default_flow_style=False, sort_keys=False)

        counts[agent] = len(new_entries)
        logger.info(f"  {agent}: {len(new_entries)} new regression entries → {output_file}")

    return counts


def main() -> None:
    """CLI entry point for adversarial regression generation."""
    parser = argparse.ArgumentParser(
        description="Generate regression YAML from failed adversarial verdicts"
    )
    parser.add_argument(
        "--verdicts",
        type=Path,
        required=True,
        help="Directory containing adversarial verdict JSONL",
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Directory for regression YAML output"
    )
    args = parser.parse_args()

    failures = extract_failures(args.verdicts)
    if not failures:
        logger.info("No failed adversarial verdicts found.")
        return

    logger.info(f"Found {len(failures)} failed adversarial verdicts.")

    entries = [generate_regression_entry(v) for v in failures]
    counts = write_regression_yaml(entries, args.output)

    total = sum(counts.values())
    logger.info(f"Generated {total} regression entries across {len(counts)} agents.")


if __name__ == "__main__":
    main()
