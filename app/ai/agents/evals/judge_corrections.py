"""Generate structured correction YAML from calibration disagreements.

Reads human label files (traces/{agent}_human_labels.jsonl) and verdict files
(traces/{agent}_verdicts.jsonl), identifies false positive/negative cases where
the judge verdict disagrees with the human label, and writes per-agent
correction YAML files to traces/corrections/{agent}_judge_corrections.yaml.

CLI: python -m app.ai.agents.evals.judge_corrections \
       --traces-dir traces/ --output traces/corrections/
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.ai.agents.evals.calibration import load_human_labels
from app.ai.agents.evals.schemas import HumanLabel
from app.core.logging import get_logger

logger = get_logger(__name__)

# 7 LLM-judged agents (accessibility + outlook_fixer are fully deterministic)
LLM_JUDGED_AGENTS: frozenset[str] = frozenset(
    {
        "scaffolder",
        "dark_mode",
        "content",
        "personalisation",
        "code_reviewer",
        "knowledge",
        "innovation",
    }
)

MAX_CORRECTIONS_PER_CRITERION = 3


def _load_verdicts_with_reasoning(
    path: Path,
) -> dict[tuple[str, str], tuple[bool, str]]:
    """Load judge verdicts with reasoning text.

    Returns:
        Lookup mapping (trace_id, criterion) -> (passed, reasoning).
    """
    lookup: dict[tuple[str, str], tuple[bool, str]] = {}
    with path.open() as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            verdict = json.loads(stripped)
            if verdict.get("error"):
                continue
            trace_id: str = verdict["trace_id"]
            for cr in verdict.get("criteria_results", []):
                lookup[(trace_id, cr["criterion"])] = (
                    cr["passed"],
                    cr.get("reasoning", ""),
                )
    return lookup


def _extract_disagreements(
    labels: list[HumanLabel],
    verdict_lookup: dict[tuple[str, str], tuple[bool, str]],
) -> list[dict[str, Any]]:
    """Find cases where judge verdict disagrees with human label.

    Returns disagreements sorted by reasoning length ascending
    (shorter reasoning = less confident judge = more useful correction).
    """
    disagreements: list[dict[str, Any]] = []

    for label in labels:
        key = (label.trace_id, label.criterion)
        match = verdict_lookup.get(key)
        if match is None:
            continue
        judge_passed, reasoning = match

        is_fp = judge_passed and not label.human_pass
        is_fn = not judge_passed and label.human_pass

        if is_fp or is_fn:
            disagreements.append(
                {
                    "trace_id": label.trace_id,
                    "criterion": label.criterion,
                    "judge_passed": judge_passed,
                    "human_passed": label.human_pass,
                    "judge_reasoning": reasoning,
                    "error_type": "false_positive" if is_fp else "false_negative",
                }
            )

    disagreements.sort(key=lambda d: len(d["judge_reasoning"]))
    return disagreements


def _build_corrections(
    agent: str,
    disagreements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build YAML-serializable correction dict from disagreements.

    Groups by criterion and caps at MAX_CORRECTIONS_PER_CRITERION per criterion.
    """
    by_criterion: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in disagreements:
        by_criterion[d["criterion"]].append(d)

    corrections: list[dict[str, Any]] = []
    for criterion in sorted(by_criterion):
        cases = by_criterion[criterion][:MAX_CORRECTIONS_PER_CRITERION]
        for case in cases:
            said = "PASS" if case["judge_passed"] else "FAIL"
            correct = "FAIL" if case["judge_passed"] else "PASS"
            reasoning_preview = case["judge_reasoning"][:120]
            corrections.append(
                {
                    "criterion": case["criterion"],
                    "type": case["error_type"],
                    "trace_id": case["trace_id"],
                    "judge_said": said,
                    "correct_answer": correct,
                    "judge_reasoning": case["judge_reasoning"],
                    "pattern": (
                        f"Judge incorrectly said {said}. Reasoning was: {reasoning_preview}"
                    ),
                }
            )

    return {
        "agent": agent,
        "generated": datetime.now(tz=UTC).isoformat(),
        "correction_count": len(corrections),
        "corrections": corrections,
    }


def generate_corrections(
    traces_dir: Path,
    output_dir: Path,
) -> list[Path]:
    """Generate correction YAML files for all LLM-judged agents.

    Args:
        traces_dir: Directory containing *_human_labels.jsonl and *_verdicts.jsonl.
        output_dir: Directory to write *_judge_corrections.yaml files.

    Returns:
        List of paths to written correction files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for agent in sorted(LLM_JUDGED_AGENTS):
        labels_path = traces_dir / f"{agent}_human_labels.jsonl"
        verdicts_path = traces_dir / f"{agent}_verdicts.jsonl"

        if not labels_path.exists():
            logger.debug(
                "judge_corrections.skip_missing_labels",
                agent=agent,
                path=str(labels_path),
            )
            continue
        if not verdicts_path.exists():
            logger.debug(
                "judge_corrections.skip_missing_verdicts",
                agent=agent,
                path=str(verdicts_path),
            )
            continue

        labels = load_human_labels(labels_path)
        if not labels:
            continue

        verdict_lookup = _load_verdicts_with_reasoning(verdicts_path)
        disagreements = _extract_disagreements(labels, verdict_lookup)

        if not disagreements:
            logger.info(
                "judge_corrections.no_disagreements",
                agent=agent,
            )
            continue

        corrections = _build_corrections(agent, disagreements)
        out_path = output_dir / f"{agent}_judge_corrections.yaml"
        with out_path.open("w") as f:
            yaml.dump(corrections, f, default_flow_style=False, sort_keys=False)

        written.append(out_path)
        logger.info(
            "judge_corrections.generate_completed",
            agent=agent,
            corrections=corrections["correction_count"],
        )

    return written


def main() -> None:
    """CLI entry point for judge correction generation."""
    parser = argparse.ArgumentParser(
        description="Generate judge correction YAML from calibration disagreements"
    )
    parser.add_argument(
        "--traces-dir",
        default="traces/",
        help="Directory containing label and verdict JSONL files",
    )
    parser.add_argument(
        "--output",
        default="traces/corrections/",
        help="Directory to write correction YAML files",
    )
    args = parser.parse_args()

    written = generate_corrections(Path(args.traces_dir), Path(args.output))

    if written:
        logger.info(
            "judge_corrections.summary",
            files_written=len(written),
            paths=[str(p) for p in written],
        )
    else:
        logger.info("judge_corrections.no_corrections_generated")


if __name__ == "__main__":
    main()
