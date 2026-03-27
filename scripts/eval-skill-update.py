#!/usr/bin/env python3
"""Detect eval-driven skill file update candidates and optionally apply patches.

Usage:
    uv run python scripts/eval-skill-update.py --dry-run
    uv run python scripts/eval-skill-update.py --dry-run --agent scaffolder
    uv run python scripts/eval-skill-update.py --threshold 0.90
    uv run python scripts/eval-skill-update.py  # creates git branch with patches
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.agents.evals.skill_updater import (
    SkillUpdateDetector,
    apply_patches,
    format_candidate_report,
    format_patch_report,
)


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect skill file update candidates from eval failures",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print candidates and patches without creating git branch (default: off)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Pass rate threshold below which updates are proposed (default: 0.80)",
    )
    parser.add_argument(
        "--min-failures",
        type=int,
        default=5,
        help="Minimum failure count to trigger update (default: 5)",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Filter to a single agent (e.g., scaffolder)",
    )
    parser.add_argument(
        "--analysis",
        type=str,
        default="traces/analysis.json",
        help="Path to analysis.json (default: traces/analysis.json)",
    )
    args = parser.parse_args()

    detector = SkillUpdateDetector(
        analysis_path=Path(args.analysis),
        threshold=args.threshold,
        min_failures=args.min_failures,
    )

    # Step 1: Detect candidates
    candidates = detector.detect_update_candidates(agent_filter=args.agent)

    if not candidates:
        print("\nNo skill update candidates found.")
        print(f"  Threshold: {args.threshold:.0%}, Min failures: {args.min_failures}")
        return 0

    print(f"\n{format_candidate_report(candidates)}")

    # Step 2: Generate patches via LLM
    patches = []
    for candidate in candidates:
        if candidate.source == "tool_usage":
            # Tool usage promotions are reported but not auto-patched
            continue
        patch = await detector.generate_patch(candidate)
        if patch:
            patches.append(patch)

    if patches:
        print(f"\n{format_patch_report(patches)}")

    # Step 3: Apply patches (create branch) unless dry-run
    if args.dry_run:
        print("\n[dry-run] No git branch created.")
        return 1 if patches else 0

    branch = apply_patches(patches, dry_run=False)
    if branch:
        print(f"\nBranch created: {branch}")
        print(f"  {len(patches)} file(s) patched. Review and open a PR.")
        return 1

    print("\nNo patches to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
