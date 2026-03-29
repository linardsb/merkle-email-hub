"""SKILL.md A/B test runner -- compare current vs proposed SKILL.md via eval suite.

Usage:
    python -m app.ai.agents.evals.skill_ab \
        --agent scaffolder \
        --proposed path/to/proposed_SKILL.md \
        --output traces/ab/ \
        [--dry-run] \
        [--threshold 0.05]

Runs the eval suite twice (current SKILL.md vs proposed), compares
per-criterion pass rates, and recommends merge/reject.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from app.ai.agents.evals.error_analysis import compute_pass_rates, load_verdicts
from app.ai.agents.evals.schemas import (
    SkillABCriterionDelta,
    SkillABResult,
)
from app.ai.agents.skill_override import clear_override, set_override
from app.core.logging import get_logger

logger = get_logger(__name__)

# Map agent names to their SKILL.md paths
_SKILL_PATHS: dict[str, Path] = {
    "scaffolder": Path("app/ai/agents/scaffolder/SKILL.md"),
    "dark_mode": Path("app/ai/agents/dark_mode/SKILL.md"),
    "content": Path("app/ai/agents/content/SKILL.md"),
    "outlook_fixer": Path("app/ai/agents/outlook_fixer/SKILL.md"),
    "accessibility": Path("app/ai/agents/accessibility/SKILL.md"),
    "personalisation": Path("app/ai/agents/personalisation/SKILL.md"),
    "code_reviewer": Path("app/ai/agents/code_reviewer/SKILL.md"),
    "knowledge": Path("app/ai/agents/knowledge/SKILL.md"),
    "innovation": Path("app/ai/agents/innovation/SKILL.md"),
}

DEGRADATION_THRESHOLD = 0.05  # 5%
MIN_CASES = 10


async def _run_eval_variant(
    agent: str,
    variant_label: str,
    output_dir: Path,
    *,
    dry_run: bool = False,
) -> dict[str, dict[str, float]]:
    """Run traces + judges for one variant, return pass rates.

    Returns: {agent: {criterion: pass_rate}}
    """
    from app.ai.agents.evals.judge_runner import run_judge
    from app.ai.agents.evals.runner import run_agent

    trace_file = output_dir / f"ab_{agent}_{variant_label}_traces.jsonl"
    verdict_file = output_dir / f"ab_{agent}_{variant_label}_verdicts.jsonl"

    # Generate traces (writes to default location)
    await run_agent(agent, output_dir, dry_run=dry_run)

    # Rename the default trace file to variant-specific name
    default_trace = output_dir / f"{agent}_traces.jsonl"
    if default_trace.exists():
        default_trace.rename(trace_file)

    # Run judges
    await run_judge(
        agent=agent,
        traces_path=trace_file,
        output_path=verdict_file,
        provider_name=None,
        model_override=None,
        batch_size=5,
        delay=2.0,
        dry_run=dry_run,
    )

    # Compute pass rates
    verdicts = load_verdicts(verdict_file)
    return compute_pass_rates(verdicts)


def compare_variants(
    agent: str,
    rates_a: dict[str, dict[str, float]],
    rates_b: dict[str, dict[str, float]],
    total_cases: int,
    threshold: float = DEGRADATION_THRESHOLD,
    min_cases: int = MIN_CASES,
) -> SkillABResult:
    """Compare pass rates between variant A (current) and variant B (proposed).

    Auto-rejects if any criterion drops by more than threshold.
    """
    agent_rates_a = rates_a.get(agent, {})
    agent_rates_b = rates_b.get(agent, {})

    all_criteria = sorted({*agent_rates_a, *agent_rates_b})

    criteria_deltas: list[SkillABCriterionDelta] = []
    degraded: list[str] = []
    improved: list[str] = []

    for criterion in all_criteria:
        rate_a = agent_rates_a.get(criterion, 0.0)
        rate_b = agent_rates_b.get(criterion, 0.0)
        delta = rate_b - rate_a
        is_degraded = delta < -threshold

        criteria_deltas.append(
            SkillABCriterionDelta(
                criterion=criterion,
                variant_a_rate=round(rate_a, 4),
                variant_b_rate=round(rate_b, 4),
                delta=round(delta, 4),
                is_degraded=is_degraded,
            )
        )

        if is_degraded:
            degraded.append(criterion)
        elif delta > threshold:
            improved.append(criterion)

    # Overall pass rates (average across criteria)
    overall_a = sum(agent_rates_a.values()) / len(agent_rates_a) if agent_rates_a else 0.0
    overall_b = sum(agent_rates_b.values()) / len(agent_rates_b) if agent_rates_b else 0.0
    overall_delta = overall_b - overall_a

    # Recommendation logic
    if total_cases < min_cases:
        recommendation = "needs_more_data"
        rejection_reason = (
            f"Only {total_cases} test cases; minimum {min_cases} required for reliable comparison."
        )
    elif degraded:
        recommendation = "reject"
        rejection_reason = (
            f"Proposed SKILL.md degrades {len(degraded)} criterion/criteria "
            f"by >{threshold:.0%}: {', '.join(degraded)}."
        )
    else:
        recommendation = "merge"
        rejection_reason = None

    return SkillABResult(
        agent=agent,
        variant_a_label="current",
        variant_b_label="proposed",
        variant_a_overall_pass_rate=round(overall_a, 4),
        variant_b_overall_pass_rate=round(overall_b, 4),
        overall_delta=round(overall_delta, 4),
        criteria_deltas=criteria_deltas,
        degraded_criteria=degraded,
        improved_criteria=improved,
        total_cases=total_cases,
        recommendation=recommendation,
        rejection_reason=rejection_reason,
    )


def build_ab_report(
    results: list[SkillABResult],
    threshold: float = DEGRADATION_THRESHOLD,
    min_cases: int = MIN_CASES,
) -> dict[str, Any]:
    """Build JSON-serializable A/B test report."""
    return {
        "degradation_threshold": threshold,
        "min_cases_required": min_cases,
        "results": [
            {
                "agent": r.agent,
                "variant_a_label": r.variant_a_label,
                "variant_b_label": r.variant_b_label,
                "variant_a_overall_pass_rate": r.variant_a_overall_pass_rate,
                "variant_b_overall_pass_rate": r.variant_b_overall_pass_rate,
                "overall_delta": r.overall_delta,
                "recommendation": r.recommendation,
                "rejection_reason": r.rejection_reason,
                "total_cases": r.total_cases,
                "degraded_criteria": r.degraded_criteria,
                "improved_criteria": r.improved_criteria,
                "criteria_deltas": [
                    {
                        "criterion": cd.criterion,
                        "variant_a_rate": cd.variant_a_rate,
                        "variant_b_rate": cd.variant_b_rate,
                        "delta": cd.delta,
                        "is_degraded": cd.is_degraded,
                    }
                    for cd in r.criteria_deltas
                ],
            }
            for r in results
        ],
    }


async def run_ab_test(
    agent: str,
    proposed_path: Path,
    output_dir: Path,
    *,
    dry_run: bool = False,
    threshold: float = DEGRADATION_THRESHOLD,
    min_cases: int = MIN_CASES,
) -> SkillABResult:
    """Run A/B test comparing current vs proposed SKILL.md.

    1. Read current SKILL.md from disk
    2. Run eval with current content (variant A)
    3. Run eval with proposed content (variant B)
    4. Compare pass rates
    5. Return result with recommendation
    """
    skill_path = _SKILL_PATHS.get(agent)
    if skill_path is None:
        msg = f"Unknown agent: {agent}"
        raise ValueError(msg)

    current_content = skill_path.read_text(encoding="utf-8")
    proposed_content = proposed_path.read_text(encoding="utf-8")

    try:
        # Variant A: run with current SKILL.md
        logger.info(f"=== Variant A: current SKILL.md ({agent}) ===")
        set_override(agent, current_content)
        rates_a = await _run_eval_variant(agent, "A", output_dir, dry_run=dry_run)

        # Variant B: run with proposed SKILL.md
        logger.info(f"=== Variant B: proposed SKILL.md ({agent}) ===")
        set_override(agent, proposed_content)
        rates_b = await _run_eval_variant(agent, "B", output_dir, dry_run=dry_run)
    finally:
        # Always clean up override
        clear_override(agent)

    # Count test cases from trace file
    trace_a = output_dir / f"ab_{agent}_A_traces.jsonl"
    total_cases = sum(1 for line in trace_a.open(encoding="utf-8") if line.strip())

    return compare_variants(agent, rates_a, rates_b, total_cases, threshold, min_cases)


async def main() -> None:
    """CLI entrypoint for SKILL.md A/B testing."""
    parser = argparse.ArgumentParser(description="A/B test SKILL.md changes against eval suite")
    parser.add_argument(
        "--agent",
        choices=list(_SKILL_PATHS.keys()),
        required=True,
        help="Agent to test",
    )
    parser.add_argument(
        "--proposed",
        type=Path,
        required=True,
        help="Path to proposed SKILL.md file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("traces"),
        help="Output directory for traces and report (default: traces/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use mock traces instead of real LLM calls",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEGRADATION_THRESHOLD,
        help=f"Max acceptable drop per criterion (default: {DEGRADATION_THRESHOLD})",
    )
    parser.add_argument(
        "--min-cases",
        type=int,
        default=MIN_CASES,
        help=f"Minimum test cases for reliable comparison (default: {MIN_CASES})",
    )
    args = parser.parse_args()

    if not args.proposed.exists():
        logger.error(f"Proposed SKILL.md not found: {args.proposed}")
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)

    result = await run_ab_test(
        args.agent,
        args.proposed,
        args.output,
        dry_run=args.dry_run,
        threshold=args.threshold,
        min_cases=args.min_cases,
    )

    # Write report
    report = build_ab_report([result], args.threshold, args.min_cases)
    report_path = args.output / f"ab_{args.agent}_report.json"
    with report_path.open("w") as f:
        json.dump(report, f, indent=2)

    # Log summary
    logger.info(f"=== A/B Test Result: {args.agent} ===")
    logger.info(f"Current:  {result.variant_a_overall_pass_rate:.1%} overall pass rate")
    logger.info(f"Proposed: {result.variant_b_overall_pass_rate:.1%} overall pass rate")
    logger.info(f"Delta:    {result.overall_delta:+.1%}")

    for cd in result.criteria_deltas:
        marker = (
            "DEGRADED" if cd.is_degraded else ("IMPROVED" if cd.delta > args.threshold else "~")
        )
        logger.info(
            f"  {cd.criterion}: {cd.variant_a_rate:.1%} -> {cd.variant_b_rate:.1%} "
            f"({cd.delta:+.1%}) [{marker}]"
        )

    logger.info(f"Recommendation: {result.recommendation.upper()}")
    if result.rejection_reason:
        logger.info(f"Reason: {result.rejection_reason}")
    logger.info(f"Full report: {report_path}")

    # Exit code: 1 if rejected, 0 otherwise
    if result.recommendation == "reject":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
