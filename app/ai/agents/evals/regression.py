"""Regression detection: compare current eval results against baseline.

Compares per-criterion pass rates from current eval run against stored
baseline. Flags regression if any criterion drops by more than tolerance.

CLI: python -m app.ai.agents.evals.regression \
       --current traces/analysis.json \
       --baseline traces/baseline.json \
       --tolerance 0.10 \
       [--update-baseline]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import RegressionReport
from app.core.logging import get_logger

logger = get_logger(__name__)

# Per-agent regression tolerance: if any single agent's pass rate drops by
# more than this many percentage points, it's flagged as a regression.
# This is stricter than the global tolerance CLI flag — it catches cases
# where overall pass rate holds but one agent silently degrades.
AGENT_REGRESSION_TOLERANCE = 0.03  # 3 percentage points


def is_agent_regression(before: float, after: float) -> bool:
    """True if an agent's overall pass rate dropped by more than 3pp."""
    return (before - after) > AGENT_REGRESSION_TOLERANCE


def compare_pass_rates(
    current: dict[str, dict[str, float]],
    baseline: dict[str, dict[str, float]],
    tolerance: float,
) -> list[RegressionReport]:
    """Compare pass rates per agent, flag regressions beyond tolerance.

    Args:
        current: {agent: {criterion: pass_rate}} from current run
        baseline: same format from baseline
        tolerance: max acceptable drop (e.g., 0.10 = 10%)
    """
    reports: list[RegressionReport] = []

    all_agents = sorted(set(list(current.keys()) + list(baseline.keys())))

    for agent in all_agents:
        curr_rates = current.get(agent, {})
        base_rates = baseline.get(agent, {})

        if not base_rates:
            curr_avg = sum(curr_rates.values()) / len(curr_rates) if curr_rates else 0.0
            reports.append(
                RegressionReport(
                    agent=agent,
                    current_pass_rate=curr_avg,
                    baseline_pass_rate=0.0,
                    delta=curr_avg,
                    regressed_criteria=[],
                    improved_criteria=list(curr_rates.keys()),
                    is_regression=False,
                )
            )
            continue

        regressed: list[str] = []
        improved: list[str] = []

        all_criteria = sorted(set(list(curr_rates.keys()) + list(base_rates.keys())))
        for criterion in all_criteria:
            curr_val = curr_rates.get(criterion, 0.0)
            base_val = base_rates.get(criterion, 0.0)
            delta = curr_val - base_val

            if delta < -tolerance:
                regressed.append(criterion)
            elif delta > tolerance:
                improved.append(criterion)

        curr_avg = sum(curr_rates.values()) / len(curr_rates) if curr_rates else 0.0
        base_avg = sum(base_rates.values()) / len(base_rates) if base_rates else 0.0

        # Flag as regression if any criterion regressed OR if the agent's
        # overall pass rate dropped by more than 3 percentage points.
        agent_regressed = len(regressed) > 0 or is_agent_regression(base_avg, curr_avg)

        reports.append(
            RegressionReport(
                agent=agent,
                current_pass_rate=round(curr_avg, 4),
                baseline_pass_rate=round(base_avg, 4),
                delta=round(curr_avg - base_avg, 4),
                regressed_criteria=regressed,
                improved_criteria=improved,
                is_regression=agent_regressed,
            )
        )

    return reports


def build_regression_report(reports: list[RegressionReport]) -> dict[str, Any]:
    """Build JSON-serializable regression report."""
    any_regression = any(r.is_regression for r in reports)

    return {
        "has_regression": any_regression,
        "agents_checked": len(reports),
        "agents_regressed": sum(1 for r in reports if r.is_regression),
        "details": [
            {
                "agent": r.agent,
                "current_pass_rate": r.current_pass_rate,
                "baseline_pass_rate": r.baseline_pass_rate,
                "delta": r.delta,
                "is_regression": r.is_regression,
                "regressed_criteria": r.regressed_criteria,
                "improved_criteria": r.improved_criteria,
            }
            for r in reports
        ],
    }


def main() -> None:
    """CLI entry point for regression detection."""
    parser = argparse.ArgumentParser(description="Detect eval regressions vs baseline")
    parser.add_argument("--current", required=True, help="Path to current analysis JSON")
    parser.add_argument("--baseline", required=True, help="Path to baseline analysis JSON")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.10,
        help="Max acceptable drop (default: 0.10)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current results",
    )
    args = parser.parse_args()

    current_path = Path(args.current)
    baseline_path = Path(args.baseline)

    with current_path.open() as f:
        current_data = json.load(f)
    current_rates: dict[str, dict[str, float]] = current_data.get("pass_rates", {})

    if not baseline_path.exists():
        logger.info(f"No baseline found at {baseline_path}. Creating from current run.")
        shutil.copy2(current_path, baseline_path)
        logger.info(f"Baseline created: {baseline_path}")
        return

    with baseline_path.open() as f:
        baseline_data = json.load(f)
    baseline_rates: dict[str, dict[str, float]] = baseline_data.get("pass_rates", {})

    reports = compare_pass_rates(current_rates, baseline_rates, args.tolerance)
    report = build_regression_report(reports)

    logger.info(f"=== Regression Check (tolerance={args.tolerance:.0%}) ===")
    for detail in report["details"]:
        status = "REGRESSED" if detail["is_regression"] else "OK"
        logger.info(
            f"  {detail['agent']}: {detail['baseline_pass_rate']:.1%} -> "
            f"{detail['current_pass_rate']:.1%} "
            f"({detail['delta']:+.1%}) [{status}]"
        )
        if detail["regressed_criteria"]:
            logger.info(f"    Regressed: {', '.join(detail['regressed_criteria'])}")

    if args.update_baseline and not report["has_regression"]:
        shutil.copy2(current_path, baseline_path)
        logger.info(f"Baseline updated: {baseline_path}")
    elif args.update_baseline and report["has_regression"]:
        logger.info("Baseline NOT updated (regression detected).")

    if report["has_regression"]:
        logger.info(f"REGRESSION DETECTED — {report['agents_regressed']} agent(s) regressed.")
        sys.exit(1)
    else:
        logger.info("No regressions detected.")


if __name__ == "__main__":
    main()
