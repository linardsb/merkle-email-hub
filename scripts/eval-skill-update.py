#!/usr/bin/env python3
"""Detect eval-driven skill file update candidates and optionally apply patches.

Usage:
    uv run python scripts/eval-skill-update.py --dry-run
    uv run python scripts/eval-skill-update.py --dry-run --agent scaffolder
    uv run python scripts/eval-skill-update.py --threshold 0.90
    uv run python scripts/eval-skill-update.py  # creates git branch with patches
    uv run python scripts/eval-skill-update.py rollback dark_mode client_behavior 1.0.0
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.agents.evals.schemas import SkillFilePatch
from app.ai.agents.evals.skill_updater import (
    SkillUpdateDetector,
    apply_patches,
    format_candidate_report,
    format_patch_report,
)


def _handle_rollback(args: argparse.Namespace) -> int:
    """Pin a skill to a specific version."""
    from app.ai.agents.skill_version import list_skill_versions, pin_skill

    try:
        pin_skill(args.agent, args.skill, args.version)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Pinned {args.agent}/{args.skill} → v{args.version}")

    versions = list_skill_versions(args.agent, args.skill)
    if versions:
        print("\nVersion history:")
        for entry in versions:
            pin_marker = " ← PINNED" if entry.version == args.version else ""
            rate = (
                f" pass_rate={entry.eval_pass_rate:.0%}" if entry.eval_pass_rate is not None else ""
            )
            print(
                f"  {entry.version}: {entry.hash} ({entry.date}, {entry.source}{rate}){pin_marker}"
            )
    return 0


async def _handle_detect(args: argparse.Namespace) -> int:
    """Detect candidates and optionally apply patches (default command)."""
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
    patches: list[SkillFilePatch] = []
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


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect skill file update candidates from eval failures",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Rollback subcommand
    rollback_parser = subparsers.add_parser(
        "rollback",
        help="Pin a skill to a prior version",
    )
    rollback_parser.add_argument("agent", type=str, help="Agent name (e.g., dark_mode)")
    rollback_parser.add_argument("skill", type=str, help="Skill name (e.g., client_behavior)")
    rollback_parser.add_argument("version", type=str, help="Version to pin (e.g., 1.0.0)")

    # Default detect/patch flags (work without a subcommand)
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

    if args.command == "rollback":
        return _handle_rollback(args)

    return await _handle_detect(args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
