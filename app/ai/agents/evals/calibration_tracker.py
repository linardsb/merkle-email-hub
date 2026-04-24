"""Calibration delta tracking: compare TPR/TNR against baseline.

Compares per-criterion TPR/TNR from current calibration against stored
baseline. Flags regression if any criterion's TPR or TNR drops by more
than the threshold (default 5 percentage points).

CLI: python -m app.ai.agents.evals.calibration_tracker \
       --current traces/ \
       --baseline traces/calibration_baseline.json \
       [--threshold 0.05] \
       [--update-baseline]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import CalibrationDelta
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default threshold: flag regression if TPR or TNR drops by more than 5pp.
CALIBRATION_REGRESSION_THRESHOLD = 0.05


def load_calibration_reports(traces_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all {agent}_calibration.json files from a traces directory.

    Returns:
        Mapping of agent name to the parsed calibration report dict.
    """
    reports: dict[str, dict[str, Any]] = {}
    for path in sorted(traces_dir.glob("*_calibration.json")):
        # e.g. "scaffolder_calibration.json" → "scaffolder"
        agent = path.name.removesuffix("_calibration.json")
        if not agent or agent == path.name:
            continue
        with path.open() as f:
            reports[agent] = json.load(f)
    return reports


def extract_metrics(
    reports: dict[str, dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Extract flat ``{agent:criterion: {tpr, tnr}}`` from calibration reports."""
    metrics: dict[str, dict[str, float]] = {}
    for report in reports.values():
        for detail in report.get("details", []):
            key = f"{detail['agent']}:{detail['criterion']}"
            metrics[key] = {"tpr": float(detail["tpr"]), "tnr": float(detail["tnr"])}
    return metrics


def load_baseline(path: Path) -> dict[str, dict[str, float]]:
    """Read calibration baseline JSON. Returns empty dict if file missing."""
    if not path.exists():
        return {}
    with path.open() as f:
        data: dict[str, dict[str, float]] = json.load(f)
    return data


def save_baseline(metrics: dict[str, dict[str, float]], path: Path) -> None:
    """Snapshot current metrics as new baseline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(metrics, f, indent=2)


def compare_calibration(
    current: dict[str, dict[str, float]],
    baseline: dict[str, dict[str, float]],
    threshold: float = CALIBRATION_REGRESSION_THRESHOLD,
) -> list[CalibrationDelta]:
    """Compute per-criterion TPR/TNR deltas. Flag regressions beyond *threshold*."""
    all_keys = sorted(set(list(current.keys()) + list(baseline.keys())))
    deltas: list[CalibrationDelta] = []

    for key in all_keys:
        curr = current.get(key, {"tpr": 0.0, "tnr": 0.0})
        base = baseline.get(key, {"tpr": 0.0, "tnr": 0.0})

        tpr_delta = curr["tpr"] - base["tpr"]
        tnr_delta = curr["tnr"] - base["tnr"]

        # New criteria (not in baseline) are never flagged as regressions.
        is_new = key not in baseline
        regressed = not is_new and (tpr_delta < -threshold or tnr_delta < -threshold)

        parts = key.split(":", 1)
        agent = parts[0]
        criterion = parts[1] if len(parts) > 1 else key

        deltas.append(
            CalibrationDelta(
                agent=agent,
                criterion=criterion,
                tpr_before=round(base["tpr"], 4),
                tpr_after=round(curr["tpr"], 4),
                tpr_delta=round(tpr_delta, 4),
                tnr_before=round(base["tnr"], 4),
                tnr_after=round(curr["tnr"], 4),
                tnr_delta=round(tnr_delta, 4),
                regressed=regressed,
            )
        )

    return deltas


def build_delta_report(deltas: list[CalibrationDelta]) -> dict[str, Any]:
    """Build JSON-serializable calibration delta report."""
    has_regression = any(d.regressed for d in deltas)
    improved = [d for d in deltas if d.tpr_delta > 0.0 or d.tnr_delta > 0.0]

    return {
        "has_regression": has_regression,
        "threshold": CALIBRATION_REGRESSION_THRESHOLD,
        "criteria_checked": len(deltas),
        "criteria_regressed": sum(1 for d in deltas if d.regressed),
        "criteria_improved": len(improved),
        "details": [
            {
                "agent": d.agent,
                "criterion": d.criterion,
                "tpr_before": d.tpr_before,
                "tpr_after": d.tpr_after,
                "tpr_delta": d.tpr_delta,
                "tnr_before": d.tnr_before,
                "tnr_after": d.tnr_after,
                "tnr_delta": d.tnr_delta,
                "regressed": d.regressed,
            }
            for d in deltas
        ],
    }


def main() -> None:
    """CLI entry point for calibration delta tracking."""
    parser = argparse.ArgumentParser(description="Compare calibration TPR/TNR against baseline")
    parser.add_argument(
        "--current", required=True, help="Path to traces directory with *_calibration.json files"
    )
    parser.add_argument("--baseline", required=True, help="Path to calibration baseline JSON")
    parser.add_argument(
        "--threshold",
        type=float,
        default=CALIBRATION_REGRESSION_THRESHOLD,
        help=f"Max acceptable TPR/TNR drop (default: {CALIBRATION_REGRESSION_THRESHOLD})",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current results (only if no regressions)",
    )
    args = parser.parse_args()

    traces_dir = Path(args.current)
    baseline_path = Path(args.baseline)

    reports = load_calibration_reports(traces_dir)
    if not reports:
        logger.info(f"No *_calibration.json files found in {traces_dir}. Skipping.")
        return

    current_metrics = extract_metrics(reports)
    baseline_metrics = load_baseline(baseline_path)

    if not baseline_metrics:
        logger.info(f"No baseline found at {baseline_path}. Creating from current run.")
        save_baseline(current_metrics, baseline_path)
        logger.info(f"Baseline created with {len(current_metrics)} criteria: {baseline_path}")
        return

    deltas = compare_calibration(current_metrics, baseline_metrics, args.threshold)
    report = build_delta_report(deltas)

    logger.info(f"=== Calibration Delta Check (threshold={args.threshold:.0%}) ===")
    for detail in report["details"]:
        status = "REGRESSED" if detail["regressed"] else "OK"
        logger.info(
            f"  {detail['agent']}:{detail['criterion']} "
            f"— TPR {detail['tpr_before']:.2f}->{detail['tpr_after']:.2f} "
            f"({detail['tpr_delta']:+.2f}), "
            f"TNR {detail['tnr_before']:.2f}->{detail['tnr_after']:.2f} "
            f"({detail['tnr_delta']:+.2f}) [{status}]"
        )

    if args.update_baseline and not report["has_regression"]:
        save_baseline(current_metrics, baseline_path)
        logger.info(f"Baseline updated: {baseline_path}")
    elif args.update_baseline and report["has_regression"]:
        logger.info("Baseline NOT updated (regression detected).")

    if report["has_regression"]:
        regressed_count = report["criteria_regressed"]
        logger.info(
            f"CALIBRATION REGRESSION DETECTED — {regressed_count} criterion/criteria regressed."
        )
        sys.exit(1)
    else:
        logger.info("No calibration regressions detected.")


if __name__ == "__main__":
    main()
