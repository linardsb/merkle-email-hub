#!/usr/bin/env python3
"""Backfill conversion memories from snapshot test cases.

Re-runs the converter on each active snapshot case (data/debug/{case_id}/),
then persists quality data to memory, insights, and traces — seeding the
learning loop with real conversion history.

Usage:
    python scripts/backfill-conversion-memories.py [--dry-run] [--lower-threshold]

Options:
    --dry-run           Show what would be persisted without writing to DB/traces
    --traces-only       Write JSONL traces only (no DB/embeddings needed)
    --lower-threshold   Also persist clean conversions (overrides 0.8 threshold)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

import yaml  # noqa: E402

from app.core.logging import get_logger  # noqa: E402
from app.design_sync.converter_memory import (  # noqa: E402
    _CLEAN_CONFIDENCE_THRESHOLD,
    build_conversion_metadata,
    format_conversion_quality,
)
from app.design_sync.converter_service import ConversionResult, DesignConverterService  # noqa: E402
from app.design_sync.converter_traces import append_trace, build_trace  # noqa: E402
from app.design_sync.diagnose.report import (  # noqa: E402
    load_structure_from_json,
    load_tokens_from_json,
)

logger = get_logger(__name__)

_DEBUG_DIR = _PROJECT_ROOT / "data" / "debug"
_MANIFEST = _DEBUG_DIR / "manifest.yaml"


def _load_active_cases() -> list[dict[str, object]]:
    """Load active cases from manifest.yaml."""
    if not _MANIFEST.exists():
        sys.stdout.write(f"Manifest not found: {_MANIFEST}\n")
        return []
    data = yaml.safe_load(_MANIFEST.read_text())
    cases: list[dict[str, object]] = data.get("cases", [])
    return [c for c in cases if c.get("status") == "active"]


def _run_conversion(case_dir: Path) -> ConversionResult:
    """Load inputs and run the full converter pipeline."""
    structure = load_structure_from_json(case_dir / "structure.json")
    tokens = load_tokens_from_json(case_dir / "tokens.json")
    converter = DesignConverterService()
    return converter.convert(structure, tokens)


def _print_summary(case_id: str, name: str, result: ConversionResult) -> None:
    """Print a human-readable summary of conversion quality."""
    confidences = list(result.match_confidences.values())
    avg_conf = sum(confidences) / len(confidences) if confidences else 1.0
    low_conf = [idx for idx, c in result.match_confidences.items() if c < 0.6]

    sys.stdout.write(
        f"\n{'=' * 60}\n"
        f"Case {case_id}: {name}\n"
        f"  Sections: {result.sections_count}\n"
        f"  Quality warnings: {len(result.quality_warnings)}\n"
    )
    for w in result.quality_warnings:
        sys.stdout.write(f"    - [{w.severity}] {w.category}: {w.message}\n")

    sys.stdout.write(
        f"  Avg match confidence: {avg_conf:.2f}\n"
        f"  Low-confidence sections (<0.6): {low_conf or 'none'}\n"
    )

    # Check if it would be persisted
    has_issues = bool(result.quality_warnings) or any(
        c < _CLEAN_CONFIDENCE_THRESHOLD for c in confidences
    )
    sys.stdout.write(f"  Would persist to memory: {'YES' if has_issues else 'NO (clean)'}\n")


async def _persist_to_memory(
    result: ConversionResult,
    case_id: str,
    lower_threshold: bool,
) -> bool:
    """Persist conversion quality to memory. Returns True if stored."""
    from app.core.config import get_settings
    from app.core.database import get_db_context
    from app.knowledge.embedding import get_embedding_provider
    from app.memory.schemas import MemoryCreate
    from app.memory.service import MemoryService

    # Check if there are quality issues worth persisting
    confidences = list(result.match_confidences.values())
    has_issues = bool(result.quality_warnings) or any(
        c < _CLEAN_CONFIDENCE_THRESHOLD for c in confidences
    )

    if not has_issues and not lower_threshold:
        return False

    content = format_conversion_quality(result)
    if content is None and lower_threshold:
        # Force a content string for clean conversions
        avg_conf = sum(confidences) / len(confidences) if confidences else 1.0
        content = (
            f"Conversion quality report (sections={result.sections_count}, warnings=0):\n"
            f"All sections matched with avg confidence {avg_conf:.2f}.\n"
            f"Source: snapshot case {case_id}"
        )
    if content is None:
        return False

    metadata = build_conversion_metadata(result, f"snapshot_{case_id}")

    settings = get_settings()
    async with get_db_context() as db:
        embedding_provider = get_embedding_provider(settings)
        service = MemoryService(db, embedding_provider)
        await service.store(
            MemoryCreate(
                agent_type="design_sync",
                memory_type="semantic",
                content=content,
                project_id=None,
                metadata=metadata,
                is_evergreen=False,
            ),
        )

    return True


async def _persist_insights(
    result: ConversionResult,
    case_id: str,
) -> int:
    """Persist low-confidence insights. Returns count stored."""
    from app.design_sync.converter_insights import persist_conversion_insights

    return await persist_conversion_insights(result, f"snapshot_{case_id}", None)


def _persist_trace(result: ConversionResult, case_id: str) -> None:
    """Append a trace to the JSONL file."""
    trace = build_trace(result, f"snapshot_{case_id}")
    append_trace(trace)


async def main() -> None:
    dry_run = "--dry-run" in sys.argv
    traces_only = "--traces-only" in sys.argv
    lower_threshold = "--lower-threshold" in sys.argv

    cases = _load_active_cases()
    if not cases:
        sys.stdout.write("No active cases found.\n")
        return

    sys.stdout.write(f"Found {len(cases)} active snapshot case(s).\n")
    if dry_run:
        sys.stdout.write("DRY RUN — no data will be written.\n")
    elif traces_only:
        sys.stdout.write("TRACES ONLY — writing JSONL traces, skipping DB.\n")

    total_memories = 0
    total_insights = 0
    total_traces = 0

    for case in cases:
        case_id = str(case["id"])
        name = str(case.get("name", "unnamed"))
        case_dir = _DEBUG_DIR / case_id

        if not (case_dir / "structure.json").exists():
            sys.stdout.write(f"Skipping case {case_id} — no structure.json\n")
            continue

        # Run conversion
        result = _run_conversion(case_dir)
        _print_summary(case_id, name, result)

        if dry_run:
            continue

        # Persist memory + insights (requires embedding provider)
        if not traces_only:
            stored = await _persist_to_memory(result, case_id, lower_threshold)
            if stored:
                total_memories += 1
                sys.stdout.write("  -> Stored memory entry\n")

            count = await _persist_insights(result, case_id)
            total_insights += count
            if count:
                sys.stdout.write(f"  -> Stored {count} insight(s)\n")

        # Persist trace (no DB/embeddings needed)
        _persist_trace(result, case_id)
        total_traces += 1
        sys.stdout.write("  -> Appended trace\n")

    sys.stdout.write(
        f"\n{'=' * 60}\n"
        f"Backfill complete:\n"
        f"  Memory entries: {total_memories}\n"
        f"  Insights: {total_insights}\n"
        f"  Traces: {total_traces}\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
