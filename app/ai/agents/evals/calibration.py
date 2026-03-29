"""Judge calibration: compute TPR/TNR against human labels.

Human labels format (JSONL):
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "brief_fidelity",
 "human_pass": true, "notes": ""}

CLI: python -m app.ai.agents.evals.calibration \
       --verdicts traces/scaffolder_verdicts.jsonl \
       --labels traces/scaffolder_human_labels.jsonl \
       --output traces/scaffolder_calibration.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import CalibrationResult, HumanLabel
from app.core.logging import get_logger

logger = get_logger(__name__)


def load_human_labels(path: Path) -> list[HumanLabel]:
    """Load human labels from JSONL file."""
    labels: list[HumanLabel] = []
    with path.open() as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                data = json.loads(stripped)
                if data.get("human_pass") is None:
                    continue  # Skip unlabeled rows
                labels.append(
                    HumanLabel(
                        trace_id=data["trace_id"],
                        agent=data["agent"],
                        criterion=data["criterion"],
                        human_pass=data["human_pass"],
                        notes=data.get("notes", ""),
                    )
                )
    return labels


def load_judge_verdicts(path: Path) -> dict[tuple[str, str], bool]:
    """Load judge verdicts into lookup: (trace_id, criterion) -> passed."""
    lookup: dict[tuple[str, str], bool] = {}
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
                lookup[(trace_id, cr["criterion"])] = cr["passed"]
    return lookup


def calibrate(
    labels: list[HumanLabel],
    judge_lookup: dict[tuple[str, str], bool],
) -> list[CalibrationResult]:
    """Compute TPR/TNR for each (agent, criterion) pair.

    Only includes labels that have matching judge verdicts.
    """
    groups: dict[tuple[str, str], list[tuple[bool, bool]]] = defaultdict(list)

    for label in labels:
        key = (label.trace_id, label.criterion)
        judge_pass = judge_lookup.get(key)
        if judge_pass is None:
            continue
        groups[(label.agent, label.criterion)].append((judge_pass, label.human_pass))

    results: list[CalibrationResult] = []
    for (agent, criterion), pairs in sorted(groups.items()):
        tp = sum(1 for jp, hp in pairs if jp and hp)
        tn = sum(1 for jp, hp in pairs if not jp and not hp)
        fp = sum(1 for jp, hp in pairs if jp and not hp)
        fn = sum(1 for jp, hp in pairs if not jp and hp)

        results.append(
            CalibrationResult(
                agent=agent,
                criterion=criterion,
                true_positives=tp,
                true_negatives=tn,
                false_positives=fp,
                false_negatives=fn,
                total=len(pairs),
            )
        )

    return results


def build_calibration_report(results: list[CalibrationResult]) -> dict[str, Any]:
    """Build JSON-serializable calibration report."""
    criteria_details: list[dict[str, Any]] = []
    all_meet_targets = True

    for r in results:
        meets = r.meets_targets
        if not meets:
            all_meet_targets = False
        criteria_details.append(
            {
                "agent": r.agent,
                "criterion": r.criterion,
                "tpr": round(r.tpr, 4),
                "tnr": round(r.tnr, 4),
                "meets_targets": meets,
                "confusion": {
                    "tp": r.true_positives,
                    "tn": r.true_negatives,
                    "fp": r.false_positives,
                    "fn": r.false_negatives,
                },
                "total_labels": r.total,
            }
        )

    failing = [d for d in criteria_details if not d["meets_targets"]]

    return {
        "all_meet_targets": all_meet_targets,
        "total_criteria": len(results),
        "passing_criteria": len(results) - len(failing),
        "failing_criteria": len(failing),
        "target_tpr": 0.85,
        "target_tnr": 0.80,
        "details": criteria_details,
        "needs_attention": [
            {
                "agent": d["agent"],
                "criterion": d["criterion"],
                "tpr": d["tpr"],
                "tnr": d["tnr"],
            }
            for d in failing
        ],
    }


def main() -> None:
    """CLI entry point for judge calibration."""
    parser = argparse.ArgumentParser(description="Calibrate judges against human labels")
    parser.add_argument("--verdicts", required=True, help="Path to verdicts JSONL")
    parser.add_argument("--labels", required=True, help="Path to human labels JSONL")
    parser.add_argument("--output", required=True, help="Path to write calibration JSON")
    args = parser.parse_args()

    judge_lookup = load_judge_verdicts(Path(args.verdicts))
    labels = load_human_labels(Path(args.labels))

    if not labels:
        logger.error("No human labels found.")
        sys.exit(1)

    results = calibrate(labels, judge_lookup)
    report = build_calibration_report(results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2)

    logger.info("=== Judge Calibration ===")
    logger.info(f"Criteria evaluated: {report['total_criteria']}")
    logger.info(
        f"Meeting targets (TPR>{report['target_tpr']}, TNR>{report['target_tnr']}): "
        f"{report['passing_criteria']}/{report['total_criteria']}"
    )

    if report["needs_attention"]:
        logger.info("Needs attention:")
        for item in report["needs_attention"]:
            logger.info(
                f"  {item['agent']}:{item['criterion']} "
                f"— TPR={item['tpr']:.2f}, TNR={item['tnr']:.2f}"
            )

    status = "PASS" if report["all_meet_targets"] else "FAIL"
    logger.info(f"Calibration: {status}")
    logger.info(f"Report: {args.output}")


if __name__ == "__main__":
    main()
