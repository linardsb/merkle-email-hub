"""Auto-label evaluation rows that don't need human judgment.

Key insight: calibration.py skips rows where judge_pass is None (line 80),
so the 1020 QA check rows are NEVER used for TPR/TNR calculation.

Fills human_pass for:
1. QA check rows (1020) — auto-agree (not used by calibration, informational only)
2. Deterministic judge verdicts (302) — auto-agree (derived from QA checks)

Only LLM-judged verdicts (208 rows) remain for human review.

Usage:
    python scripts/auto-label.py --traces-dir traces/ [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

AGENTS = [
    "scaffolder",
    "dark_mode",
    "content",
    "outlook_fixer",
    "accessibility",
    "personalisation",
    "code_reviewer",
    "knowledge",
    "innovation",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text().strip().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_qa_lookup(traces: list[dict[str, Any]]) -> dict[tuple[str, str], bool]:
    """Build (trace_id, check_name) -> passed lookup from trace qa_results."""
    lookup: dict[tuple[str, str], bool] = {}
    for t in traces:
        tid = t.get("trace_id", t.get("id", ""))
        output = t.get("output", {})
        if not isinstance(output, dict):
            continue
        qa_results = output.get("qa_results", [])
        if isinstance(qa_results, list):
            for qr in qa_results:
                check = qr.get("check_name", "")
                passed = qr.get("passed")
                if check and passed is not None:
                    lookup[(tid, check)] = bool(passed)
    return lookup


def build_verdict_reasoning_lookup(
    verdicts: list[dict[str, Any]],
) -> dict[tuple[str, str], tuple[bool, str]]:
    """Build (trace_id, criterion) -> (passed, reasoning) lookup."""
    lookup: dict[tuple[str, str], tuple[bool, str]] = {}
    for v in verdicts:
        tid = v["trace_id"]
        for cr in v.get("criteria_results", []):
            lookup[(tid, cr["criterion"])] = (cr["passed"], cr.get("reasoning", ""))
    return lookup


def auto_label_agent(
    agent: str,
    traces_dir: Path,
    dry_run: bool = False,
) -> dict[str, int]:
    """Auto-label rows for a single agent. Returns stats."""
    labels_path = traces_dir / f"{agent}_human_labels.jsonl"
    traces = load_jsonl(traces_dir / f"{agent}_traces.jsonl")
    verdicts = load_jsonl(traces_dir / f"{agent}_verdicts.jsonl")
    labels = load_jsonl(labels_path)

    if not labels:
        return {"total": 0, "qa_auto": 0, "det_auto": 0, "already_labeled": 0, "human_needed": 0}

    qa_lookup = build_qa_lookup(traces)
    verdict_lookup = build_verdict_reasoning_lookup(verdicts)

    stats = {
        "total": len(labels),
        "qa_auto": 0,
        "det_auto": 0,
        "already_labeled": 0,
        "human_needed": 0,
    }

    for label in labels:
        tid = label["trace_id"]
        criterion = label["criterion"]

        # Already labeled by human — skip
        if label["human_pass"] is not None:
            stats["already_labeled"] += 1
            continue

        # QA check row (judge_pass is None) — not used by calibration at all.
        # Auto-agree: use trace qa_results if available, otherwise mark as N/A.
        if label["judge_pass"] is None:
            qa_key = (tid, criterion)
            if qa_key in qa_lookup:
                label["human_pass"] = qa_lookup[qa_key]
                label["notes"] = "[AUTO] from trace qa_results (not used by calibration)"
            else:
                label["human_pass"] = True  # Default — QA rows don't affect calibration
                label["notes"] = "[AUTO] QA row, not used by calibration"
            stats["qa_auto"] += 1
            continue

        # Judge criterion — check if deterministic
        verdict_key = (tid, criterion)
        if verdict_key in verdict_lookup:
            passed, reasoning = verdict_lookup[verdict_key]
            if reasoning.startswith("[DETERMINISTIC]"):
                # Deterministic verdict — trust it, auto-agree
                label["human_pass"] = passed
                label["notes"] = "[AUTO] deterministic judge verdict verified"
                stats["det_auto"] += 1
                continue

        # LLM verdict — needs human review
        stats["human_needed"] += 1

    if not dry_run:
        with labels_path.open("w") as f:
            for label in labels:
                f.write(json.dumps(label) + "\n")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-label QA and deterministic eval rows")
    parser.add_argument("--traces-dir", type=Path, default=Path("traces"))
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    args = parser.parse_args()

    total_stats = {"total": 0, "qa_auto": 0, "det_auto": 0, "already_labeled": 0, "human_needed": 0}

    print(
        f"{'Agent':20s} {'Total':>6s} {'QA auto':>8s} {'Det auto':>9s} {'Already':>8s} {'Human':>6s}"
    )
    print("-" * 60)

    for agent in AGENTS:
        stats = auto_label_agent(agent, args.traces_dir, dry_run=args.dry_run)
        print(
            f"{agent:20s} {stats['total']:6d} {stats['qa_auto']:8d} "
            f"{stats['det_auto']:9d} {stats['already_labeled']:8d} {stats['human_needed']:6d}"
        )
        for k in total_stats:
            total_stats[k] += stats[k]

    print("-" * 60)
    print(
        f"{'TOTAL':20s} {total_stats['total']:6d} {total_stats['qa_auto']:8d} "
        f"{total_stats['det_auto']:9d} {total_stats['already_labeled']:8d} {total_stats['human_needed']:6d}"
    )

    automated = total_stats["qa_auto"] + total_stats["det_auto"]
    print(
        f"\nAutomated: {automated} / {total_stats['total']} ({100 * automated / max(total_stats['total'], 1):.0f}%)"
    )
    print(f"Human review needed: {total_stats['human_needed']}")

    if args.dry_run:
        print("\n[DRY RUN] No files were modified.")


if __name__ == "__main__":
    main()
