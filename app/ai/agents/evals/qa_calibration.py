"""QA gate calibration: measure 11-point QA checks against human judgments.

Reads agent traces (which contain HTML output), runs QA checks on each,
then compares QA check pass/fail against human labels on the same traces.

CLI: python -m app.ai.agents.evals.qa_calibration \
       --traces traces/scaffolder_traces.jsonl \
       --labels traces/scaffolder_human_labels.jsonl \
       --output traces/qa_calibration.json

Human labels for QA calibration use criterion names matching QA check names:
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "dark_mode",
 "human_pass": true}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.ai.agents.evals.calibration import load_human_labels
from app.ai.agents.evals.schemas import HumanLabel, QACalibrationResult
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
    "personalisation_syntax",
]


async def run_qa_on_traces(
    traces: list[dict[str, Any]],
) -> dict[str, dict[str, bool]]:
    """Run all 11 QA checks on each trace's HTML output.

    Returns: {trace_id: {check_name: passed}}
    """
    from app.qa_engine.checks import ALL_CHECKS

    results: dict[str, dict[str, bool]] = {}

    for trace in traces:
        trace_id: str = trace["id"]
        output = trace.get("output")
        if not output:
            continue

        html: str = output.get("html", "")
        if not html:
            continue

        check_results: dict[str, bool] = {}
        for check in ALL_CHECKS:
            result = await check.run(html)
            check_results[result.check_name] = result.passed

        results[trace_id] = check_results

    return results


def calibrate_qa(
    qa_results: dict[str, dict[str, bool]],
    labels: list[HumanLabel],
) -> list[QACalibrationResult]:
    """Compare QA check results against human labels.

    Only compares labels where criterion name matches a QA check name.
    """
    groups: dict[str, list[tuple[bool, bool]]] = defaultdict(list)

    for label in labels:
        if label.criterion not in QA_CHECK_NAMES:
            continue
        trace_qa = qa_results.get(label.trace_id)
        if trace_qa is None:
            continue
        qa_pass = trace_qa.get(label.criterion)
        if qa_pass is None:
            continue
        groups[label.criterion].append((qa_pass, label.human_pass))

    results: list[QACalibrationResult] = []
    for check_name in QA_CHECK_NAMES:
        pairs = groups.get(check_name, [])
        if not pairs:
            continue

        total = len(pairs)
        agree = sum(1 for qp, hp in pairs if qp == hp)
        false_pass = sum(1 for qp, hp in pairs if qp and not hp)
        false_fail = sum(1 for qp, hp in pairs if not qp and hp)

        results.append(
            QACalibrationResult(
                check_name=check_name,
                agreement_rate=agree / total if total > 0 else 0.0,
                false_pass_rate=false_pass / total if total > 0 else 0.0,
                false_fail_rate=false_fail / total if total > 0 else 0.0,
                total=total,
            )
        )

    return results


def build_qa_report(results: list[QACalibrationResult]) -> dict[str, Any]:
    """Build JSON-serializable QA calibration report."""
    details = [
        {
            "check_name": r.check_name,
            "agreement_rate": round(r.agreement_rate, 4),
            "false_pass_rate": round(r.false_pass_rate, 4),
            "false_fail_rate": round(r.false_fail_rate, 4),
            "total_labels": r.total,
            "recommended_threshold": r.recommended_threshold,
        }
        for r in results
    ]

    avg_agreement = sum(r.agreement_rate for r in results) / len(results) if results else 0.0

    needs_tuning = [
        d for d in details if isinstance(d["agreement_rate"], float) and d["agreement_rate"] < 0.75
    ]

    return {
        "average_agreement": round(avg_agreement, 4),
        "checks_evaluated": len(results),
        "checks_needing_tuning": len(needs_tuning),
        "details": details,
        "needs_tuning": needs_tuning,
    }


def main() -> None:
    """CLI entry point for QA gate calibration."""
    parser = argparse.ArgumentParser(description="Calibrate QA gate against human labels")
    parser.add_argument("--traces", required=True, help="Path to traces JSONL (with HTML output)")
    parser.add_argument("--labels", required=True, help="Path to human labels JSONL")
    parser.add_argument("--output", required=True, help="Path to write QA calibration JSON")
    args = parser.parse_args()

    traces: list[dict[str, Any]] = []
    with Path(args.traces).open() as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                traces.append(json.loads(stripped))

    labels = load_human_labels(Path(args.labels))

    if not traces or not labels:
        logger.error("Need both traces and labels.")
        sys.exit(1)

    qa_results = asyncio.run(run_qa_on_traces(traces))

    results = calibrate_qa(qa_results, labels)
    report = build_qa_report(results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2)

    logger.info("=== QA Gate Calibration ===")
    logger.info(f"Checks evaluated: {report['checks_evaluated']}")
    logger.info(f"Average agreement: {report['average_agreement']:.1%}")
    if report["needs_tuning"]:
        logger.info(f"Needs tuning ({len(report['needs_tuning'])} checks < 75% agreement):")
        for item in report["needs_tuning"]:
            logger.info(
                f"  {item['check_name']}: {item['agreement_rate']:.1%} "
                f"(false_pass={item['false_pass_rate']:.1%}, "
                f"false_fail={item['false_fail_rate']:.1%})"
            )
    logger.info(f"Report: {args.output}")


if __name__ == "__main__":
    main()
