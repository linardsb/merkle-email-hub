"""Correction impact report: A/B comparison of judge calibration with/without corrections.

Loads calibration results from two separate directories (one from a judge run
with corrections enabled, one without) and produces a per-criterion impact
report showing TPR/TNR deltas and an overall recommendation.

CLI: python -m app.ai.agents.evals.correction_impact \
       --with-corrections traces/ \
       --without-corrections traces/no_corrections/ \
       --output traces/correction_impact_report.json \
       [--threshold 0.03]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.ai.agents.evals.calibration_tracker import (
    extract_metrics,
    load_calibration_reports,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default: flag degradation if TPR or TNR drops by more than 3pp.
DEGRADATION_THRESHOLD = 0.03


def load_calibration_pair(
    with_dir: Path,
    without_dir: Path,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Load calibration metrics from two directories.

    Returns:
        Tuple of (with_corrections_metrics, without_corrections_metrics).
    """
    with_reports = load_calibration_reports(with_dir)
    without_reports = load_calibration_reports(without_dir)
    return extract_metrics(with_reports), extract_metrics(without_reports)


def classify_impact(
    tpr_delta: float,
    tnr_delta: float,
    threshold: float = DEGRADATION_THRESHOLD,
) -> str:
    """Classify the impact of corrections on a single criterion.

    Returns:
        ``"improved"`` if either metric increased and neither regressed beyond
        threshold; ``"degraded"`` if either metric dropped beyond threshold;
        ``"no_change"`` otherwise.
    """
    degraded = tpr_delta < -threshold or tnr_delta < -threshold
    improved = (tpr_delta > 0.0 or tnr_delta > 0.0) and not degraded
    if degraded:
        return "degraded"
    if improved:
        return "improved"
    return "no_change"


def build_impact_report(
    with_metrics: dict[str, dict[str, float]],
    without_metrics: dict[str, dict[str, float]],
    threshold: float = DEGRADATION_THRESHOLD,
) -> dict[str, Any]:
    """Build a per-criterion correction impact report.

    Each key is ``agent:criterion``; value contains ``tpr_without``,
    ``tpr_with``, ``tpr_delta``, ``tnr_without``, ``tnr_with``,
    ``tnr_delta``, and ``verdict``.  A ``_summary`` key aggregates counts.
    """
    all_keys = sorted(set(list(with_metrics.keys()) + list(without_metrics.keys())))
    report: dict[str, Any] = {}

    improved_count = 0
    degraded_count = 0
    unchanged_count = 0

    for key in all_keys:
        w = with_metrics.get(key, {"tpr": 0.0, "tnr": 0.0})
        wo = without_metrics.get(key, {"tpr": 0.0, "tnr": 0.0})

        tpr_delta = round(w["tpr"] - wo["tpr"], 4)
        tnr_delta = round(w["tnr"] - wo["tnr"], 4)
        verdict = classify_impact(tpr_delta, tnr_delta, threshold)

        report[key] = {
            "tpr_without": round(wo["tpr"], 4),
            "tpr_with": round(w["tpr"], 4),
            "tpr_delta": tpr_delta,
            "tnr_without": round(wo["tnr"], 4),
            "tnr_with": round(w["tnr"], 4),
            "tnr_delta": tnr_delta,
            "verdict": verdict,
        }

        if verdict == "improved":
            improved_count += 1
        elif verdict == "degraded":
            degraded_count += 1
        else:
            unchanged_count += 1

    recommendation = "accept" if degraded_count == 0 else "review"
    report["_summary"] = {
        "criteria_improved": improved_count,
        "criteria_degraded": degraded_count,
        "criteria_unchanged": unchanged_count,
        "regression_threshold": threshold,
        "overall_recommendation": recommendation,
    }

    return report


def main() -> None:
    """CLI entry point for correction impact comparison."""
    parser = argparse.ArgumentParser(
        description="Compare judge calibration with/without corrections"
    )
    parser.add_argument(
        "--with-corrections",
        required=True,
        help="Directory with *_calibration.json from corrections-enabled run",
    )
    parser.add_argument(
        "--without-corrections",
        required=True,
        help="Directory with *_calibration.json from --no-corrections run",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path for the correction_impact_report.json output",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEGRADATION_THRESHOLD,
        help=f"Max acceptable TPR/TNR drop (default: {DEGRADATION_THRESHOLD})",
    )
    args = parser.parse_args()

    with_dir = Path(args.with_corrections)
    without_dir = Path(args.without_corrections)
    output_path = Path(args.output)

    with_metrics, without_metrics = load_calibration_pair(with_dir, without_dir)

    if not with_metrics and not without_metrics:
        logger.info("No calibration files found in either directory. Nothing to compare.")
        return

    report = build_impact_report(with_metrics, without_metrics, args.threshold)
    summary = report["_summary"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"=== Correction Impact Report (threshold={args.threshold:.0%}) ===")
    for key, entry in report.items():
        if key == "_summary":
            continue
        logger.info(
            f"  {key} — TPR {entry['tpr_without']:.2f}->{entry['tpr_with']:.2f} "
            f"({entry['tpr_delta']:+.2f}), "
            f"TNR {entry['tnr_without']:.2f}->{entry['tnr_with']:.2f} "
            f"({entry['tnr_delta']:+.2f}) [{entry['verdict']}]"
        )

    logger.info(
        f"Summary: {summary['criteria_improved']} improved, "
        f"{summary['criteria_degraded']} degraded, "
        f"{summary['criteria_unchanged']} unchanged → {summary['overall_recommendation']}"
    )

    if summary["criteria_degraded"] > 0:
        logger.info(
            f"DEGRADATION DETECTED — {summary['criteria_degraded']} criterion/criteria "
            "worsened with corrections. Review correction YAMLs."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
