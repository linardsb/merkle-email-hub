"""Scaffold human label templates from traces and verdicts.

Generates one JSONL file per agent with prefilled trace_id, agent, criterion fields.
User fills in human_pass (true/false) and optional notes.

Includes both judge criteria (from verdicts) and QA check criteria in a single file
per agent.

CLI: python -m app.ai.agents.evals.scaffold_labels \
       --verdicts traces/scaffolder_verdicts.jsonl \
       --traces traces/scaffolder_traces.jsonl \
       --output traces/scaffolder_human_labels.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

QA_CHECK_NAMES: list[str] = [
    "html_validation",
    "css_support",
    "file_size",
    "link_validation",
    "spam_score",
    "dark_mode",
    "accessibility",
    "fallback",
    "image_optimization",
    "brand_compliance",
]


def scaffold_labels(
    verdicts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    include_qa_criteria: bool = True,
) -> list[dict[str, Any]]:
    """Generate prefilled label rows from verdicts and traces.

    Each row has: trace_id, agent, criterion, judge_pass (for reference),
    human_pass (null — to be filled), notes (empty).
    """
    labels: list[dict[str, Any]] = []
    trace_ids_with_output: set[str] = {t["id"] for t in traces if t.get("output")}

    for verdict in verdicts:
        if verdict.get("error"):
            continue
        trace_id: str = verdict["trace_id"]
        if trace_id not in trace_ids_with_output:
            continue
        agent: str = verdict["agent"]

        for cr in verdict.get("criteria_results", []):
            labels.append(
                {
                    "trace_id": trace_id,
                    "agent": agent,
                    "criterion": cr["criterion"],
                    "judge_pass": cr["passed"],
                    "human_pass": None,
                    "notes": "",
                }
            )

        if include_qa_criteria:
            for check_name in QA_CHECK_NAMES:
                labels.append(
                    {
                        "trace_id": trace_id,
                        "agent": agent,
                        "criterion": check_name,
                        "judge_pass": None,
                        "human_pass": None,
                        "notes": "",
                    }
                )

    return labels


def main() -> None:
    """CLI entry point for label scaffolding."""
    parser = argparse.ArgumentParser(description="Scaffold human label templates")
    parser.add_argument("--verdicts", required=True, help="Path to verdicts JSONL")
    parser.add_argument("--traces", required=True, help="Path to traces JSONL")
    parser.add_argument("--output", required=True, help="Path to write label template JSONL")
    parser.add_argument("--no-qa", action="store_true", help="Exclude QA check criteria")
    args = parser.parse_args()

    verdicts: list[dict[str, Any]] = []
    with Path(args.verdicts).open() as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                verdicts.append(json.loads(stripped))

    traces: list[dict[str, Any]] = []
    with Path(args.traces).open() as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                traces.append(json.loads(stripped))

    if not verdicts:
        logger.error("No verdicts found.")
        sys.exit(1)

    labels = scaffold_labels(verdicts, traces, include_qa_criteria=not args.no_qa)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        for label in labels:
            f.write(json.dumps(label) + "\n")

    judge_count = sum(1 for lbl in labels if lbl["judge_pass"] is not None)
    qa_count = len(labels) - judge_count
    logger.info(
        f"Scaffolded {len(labels)} label rows "
        f"({judge_count} judge + {qa_count} QA) -> {output_path}"
    )
    logger.info("Edit the file and set human_pass to true/false for each row.")


if __name__ == "__main__":
    main()
