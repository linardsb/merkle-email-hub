"""Compare pre/post golden-reference verdicts and report flip rates.

Usage:
    python scripts/eval-compare-verdicts.py \\
        --pre-dir traces/pre_golden/ \\
        --post-dir traces/ \\
        --output traces/verdict_comparison.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FLIP_RATE_THRESHOLD = 0.20
VERDICT_SUFFIX = "_verdicts.jsonl"


def load_verdicts(path: Path) -> list[dict[str, Any]]:
    """Load JSONL verdict file, returning list of verdict dicts."""
    verdicts: list[dict[str, Any]] = []
    if not path.exists():
        return verdicts
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            verdicts.append(json.loads(line))
    return verdicts


def extract_criterion_verdicts(
    verdicts: list[dict[str, Any]],
) -> dict[tuple[str, str], bool]:
    """Flatten verdicts into {(trace_id, criterion): passed} mapping."""
    result: dict[tuple[str, str], bool] = {}
    for v in verdicts:
        trace_id = v["trace_id"]
        for cr in v.get("criteria_results", []):
            result[(trace_id, cr["criterion"])] = cr["passed"]
    return result


def compare_verdicts(
    pre_dir: Path,
    post_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Compare pre/post verdict dirs, return per-criterion flip stats."""
    results: dict[str, dict[str, Any]] = {}

    # Find all verdict files in pre_dir
    pre_files = sorted(pre_dir.glob(f"*{VERDICT_SUFFIX}"))
    if not pre_files:
        return results

    for pre_file in pre_files:
        agent = pre_file.name.replace(VERDICT_SUFFIX, "")
        post_file = post_dir / pre_file.name

        if not post_file.exists():
            continue

        pre_verdicts = extract_criterion_verdicts(load_verdicts(pre_file))
        post_verdicts = extract_criterion_verdicts(load_verdicts(post_file))

        # Group by criterion
        criteria: dict[str, list[tuple[str, str]]] = {}
        for trace_id, criterion in pre_verdicts:
            criteria.setdefault(criterion, []).append((trace_id, criterion))

        for criterion, keys in criteria.items():
            total = 0
            flips = 0
            pass_to_fail = 0
            fail_to_pass = 0
            pre_pass = 0
            post_pass = 0

            for key in keys:
                if key not in post_verdicts:
                    continue
                total += 1
                pre_val = pre_verdicts[key]
                post_val = post_verdicts[key]
                if pre_val:
                    pre_pass += 1
                if post_val:
                    post_pass += 1
                if pre_val != post_val:
                    flips += 1
                    if pre_val and not post_val:
                        pass_to_fail += 1
                    else:
                        fail_to_pass += 1

            criterion_key = f"{agent}:{criterion}"
            results[criterion_key] = {
                "agent": agent,
                "criterion": criterion,
                "total": total,
                "flips": flips,
                "flip_rate": round(flips / total, 4) if total else 0.0,
                "pass_to_fail": pass_to_fail,
                "fail_to_pass": fail_to_pass,
                "pre_pass_rate": round(pre_pass / total, 4) if total else 0.0,
                "post_pass_rate": round(post_pass / total, 4) if total else 0.0,
            }

    return results


def print_summary(results: dict[str, dict[str, Any]], threshold: float) -> None:
    """Print comparison summary table to stdout."""
    if not results:
        print("No verdict comparisons found.")
        return

    # Header
    print(
        f"\n{'Criterion':<45} {'Total':>5} {'Flips':>5} {'Rate':>6} "
        f"{'P→F':>4} {'F→P':>4} {'Pre%':>6} {'Post%':>6} {'Flag':>4}"
    )
    print("-" * 100)

    priority: list[str] = []
    for key in sorted(results):
        r = results[key]
        flag = " ⚠" if r["flip_rate"] > threshold else ""
        if r["flip_rate"] > threshold:
            priority.append(key)
        print(
            f"{key:<45} {r['total']:>5} {r['flips']:>5} "
            f"{r['flip_rate']:>5.1%} {r['pass_to_fail']:>4} "
            f"{r['fail_to_pass']:>4} {r['pre_pass_rate']:>5.1%} "
            f"{r['post_pass_rate']:>5.1%} {flag}"
        )

    print("-" * 100)
    print(f"Total criteria: {len(results)}  |  High-flip (>{threshold:.0%}): {len(priority)}")

    if priority:
        print(f"\nPriority review needed: {', '.join(priority)}")


def build_report(
    results: dict[str, dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    """Build JSON report from comparison results."""
    priority = [k for k, v in results.items() if v["flip_rate"] > threshold]
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "summary": {
            "total_criteria": len(results),
            "high_flip_criteria": len(priority),
            "threshold": threshold,
        },
        "criteria": results,
        "priority_review": sorted(priority),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Compare pre/post golden-reference verdicts",
    )
    parser.add_argument(
        "--pre-dir",
        type=Path,
        required=True,
        help="Directory with pre-golden verdict JSONL files",
    )
    parser.add_argument(
        "--post-dir",
        type=Path,
        required=True,
        help="Directory with post-golden verdict JSONL files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("traces/verdict_comparison.json"),
        help="Output JSON report path",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=FLIP_RATE_THRESHOLD,
        help=f"Flip rate threshold for priority review (default: {FLIP_RATE_THRESHOLD})",
    )
    args = parser.parse_args(argv)

    if not args.pre_dir.is_dir():
        print(f"Error: pre-dir not found: {args.pre_dir}", file=sys.stderr)
        return 1
    if not args.post_dir.is_dir():
        print(f"Error: post-dir not found: {args.post_dir}", file=sys.stderr)
        return 1

    results = compare_verdicts(args.pre_dir, args.post_dir)
    print_summary(results, args.threshold)

    report = build_report(results, args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
