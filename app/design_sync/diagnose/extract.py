"""Figma extraction script — fetch raw API JSON + run diagnostics.

Usage:
    # From existing DB connection (decrypts stored token):
    python -m app.design_sync.diagnose.extract --connection-id 8 --node-id 2833-1623

    # List frames to find email node-ids:
    python -m app.design_sync.diagnose.extract --connection-id 8 --list-frames

    # From Figma URL (reads FIGMA_TOKEN env var):
    python -m app.design_sync.diagnose.extract \
        --figma-url "https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/..." \
        --node-id 2833-1623

Output (to data/debug/{connection_id or file_key}/):
    raw_figma.json    — Raw Figma API response (full node tree)
    structure.json    — Parsed DesignFileStructure
    tokens.json       — Parsed ExtractedTokens
    report.json       — Diagnostic report (stages, section traces, data loss)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_FIGMA_API = "https://api.figma.com"
_TIMEOUT = 60.0
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_OUTPUT = _PROJECT_ROOT / "data" / "debug"


def _extract_file_key(figma_url: str) -> str:
    """Extract the file key from a Figma URL."""
    # Handles: figma.com/design/{KEY}/..., figma.com/file/{KEY}/...
    match = re.search(r"figma\.com/(?:design|file)/([a-zA-Z0-9]+)", figma_url)
    if not match:
        msg = f"Could not extract file key from URL: {figma_url}"
        raise ValueError(msg)
    return match.group(1)


async def _fetch_figma_json(
    file_key: str,
    token: str,
    node_id: str | None = None,
    depth: int | None = None,
) -> dict[str, Any]:
    """Fetch JSON from the Figma REST API."""
    headers = {"X-Figma-Token": token}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        if node_id:
            # Specific node subtree — smaller and faster
            figma_node_id = node_id.replace("-", ":")
            url = f"{_FIGMA_API}/v1/files/{file_key}/nodes"
            params: dict[str, Any] = {"ids": figma_node_id}
            if depth is not None:
                params["depth"] = depth
        else:
            # Full file
            url = f"{_FIGMA_API}/v1/files/{file_key}"
            params = {}
            if depth is not None:
                params["depth"] = depth

        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 403:
            print("ERROR: Figma token is invalid or expired.", file=sys.stderr)
            sys.exit(1)
        if resp.status_code == 404:
            print(f"ERROR: File not found: {file_key}", file=sys.stderr)
            sys.exit(1)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


async def _get_connection_creds(connection_id: int) -> tuple[str, str]:
    """Get file_key + decrypted token from a DesignConnection in the DB."""
    from app.core.database import get_db_context
    from app.design_sync.crypto import decrypt_token
    from app.design_sync.models import DesignConnection

    async with get_db_context() as db:
        conn = await db.get(DesignConnection, connection_id)
        if conn is None:
            print(f"ERROR: Connection {connection_id} not found in DB.", file=sys.stderr)
            sys.exit(1)
        token = decrypt_token(conn.encrypted_token)
        return conn.file_ref, token


async def list_frames(
    file_key: str,
    token: str,
) -> None:
    """List top-level frames in a Figma file to find email node-ids."""
    print(f"Fetching frame list for {file_key}...")
    raw = await _fetch_figma_json(file_key, token, depth=2)

    doc = raw.get("document", {})
    file_name = raw.get("name", "Untitled")
    print(f"\nFile: {file_name}")
    print("=" * 60)

    for page in doc.get("children", []):
        page_name = page.get("name", "?")
        page_id = page.get("id", "?")
        print(f"\n  Page: {page_name}  (id: {page_id})")
        print(f"  {'─' * 56}")

        for frame in page.get("children", []):
            frame_id = frame.get("id", "?")
            frame_name = frame.get("name", "?")
            bbox = frame.get("absoluteBoundingBox", {})
            w = int(bbox.get("width", 0))
            h = int(bbox.get("height", 0))
            child_count = len(frame.get("children", []))

            # Highlight likely email layouts (tall, ~600px wide)
            is_email = 400 <= w <= 800 and h > 500
            marker = " ← LIKELY EMAIL" if is_email else ""

            # URL-safe node id (colon → dash)
            url_id = frame_id.replace(":", "-")
            print(
                f"    {frame_name:40s}  id: {frame_id:12s}  "
                f"{w}x{h}  ({child_count} children){marker}"
            )
            if is_email:
                print(f"      --node-id {url_id}")

    print(f"\n{'=' * 60}")
    print("Use --node-id <id> to extract a specific email frame.")


async def extract(
    file_key: str,
    token: str,
    *,
    node_id: str | None = None,
    output_dir: Path = _DEFAULT_OUTPUT,
    label: str | None = None,
    run_diagnostics: bool = True,
) -> Path:
    """Extract Figma data and optionally run diagnostics."""
    from app.design_sync.diagnose.report import (
        dump_structure_to_json,
        dump_tokens_to_json,
        load_tokens_from_json,
        report_to_json,
    )
    from app.design_sync.diagnose.runner import DiagnosticRunner
    from app.design_sync.figma.service import FigmaDesignSyncService

    # Output directory
    dir_name = label or file_key[:12]
    out = output_dir / dir_name
    out.mkdir(parents=True, exist_ok=True)

    # 1. Fetch raw JSON from Figma API
    print(f"Fetching from Figma API (file={file_key}, node={node_id or 'full'})...")
    raw = await _fetch_figma_json(file_key, token, node_id=node_id)

    raw_path = out / "raw_figma.json"
    raw_path.write_text(json.dumps(raw, indent=2))
    raw_size = raw_path.stat().st_size
    print(f"  Saved raw JSON: {raw_path} ({raw_size:,} bytes)")

    # 2. Parse into DesignFileStructure + ExtractedTokens
    service = FigmaDesignSyncService()

    if node_id and "nodes" in raw:
        # Per-campaign mode: parse the node-specific response directly
        # This gives us ONLY the email frame, not the entire design system
        print("Parsing node subtree (per-campaign mode)...")
        figma_node_id = node_id.replace("-", ":")
        node_data = raw["nodes"].get(figma_node_id, {})
        doc = node_data.get("document", {})

        # Build structure from the single node response
        from app.design_sync.protocol import DesignFileStructure as _DFS
        from app.design_sync.protocol import DesignNode as _DN
        from app.design_sync.protocol import DesignNodeType

        parsed_node = service._parse_node(doc, current_depth=0, max_depth=None)
        # Wrap in a fake page so the pipeline sees it as a normal file
        page = _DN(
            id="0:1",
            name="Email",
            type=DesignNodeType.PAGE,
            children=[parsed_node],
        )
        structure = _DFS(
            file_name=raw.get("name", "Untitled"),
            pages=[page],
        )

        # Try to load cached tokens from a previous onboarding run
        cached_tokens_path = out / "tokens.json"
        if cached_tokens_path.exists():
            print("  Loading cached tokens from previous onboarding run...")
            tokens = load_tokens_from_json(cached_tokens_path)
        else:
            # Fallback: do a lightweight full-file fetch just for tokens
            print("  No cached tokens — fetching full file for token extraction...")
            tokens, _full_structure = await service.sync_tokens_and_structure(file_key, token)
    else:
        # Onboarding mode: full file fetch for complete token extraction
        print("Parsing full file (onboarding mode)...")
        tokens, structure = await service.sync_tokens_and_structure(file_key, token)

    # 3. Save parsed data
    structure_path = out / "structure.json"
    dump_structure_to_json(structure, structure_path)
    print(f"  Saved structure: {structure_path}")

    tokens_path = out / "tokens.json"
    dump_tokens_to_json(tokens, tokens_path)
    print(f"  Saved tokens: {tokens_path}")

    # 4. Print tree summary
    _print_tree_summary(structure)

    # 5. Run diagnostics
    if run_diagnostics:
        print("\nRunning diagnostic pipeline...")
        runner = DiagnosticRunner()
        report = runner.run_from_structure(
            structure,
            tokens,
            raw_figma_json=raw,
        )

        report_path = out / "report.json"
        report_path.write_text(report_to_json(report))
        print(f"  Saved report: {report_path}")

        # Print summary
        print(f"\n{'=' * 60}")
        print(f"  Stages completed:  {report.stages_completed}")
        print(f"  Total warnings:    {report.total_warnings}")
        print(f"  Data loss events:  {report.total_data_loss_events}")
        print(f"  Sections found:    {len(report.section_traces)}")
        print(f"  Final HTML length: {report.final_html_length:,} chars")
        print(f"  Elapsed:           {report.total_elapsed_ms:.0f}ms")

        if report.section_traces:
            print("\n  Section Traces:")
            for t in report.section_traces:
                print(
                    f"    [{t.section_idx}] {t.classified_type:12s} → "
                    f"{t.matched_component:20s} "
                    f"(conf={t.match_confidence:.1f}) "
                    f"texts={t.texts_found} imgs={t.images_found} "
                    f"btns={t.buttons_found}"
                )
                if t.unfilled_slots:
                    print(f"         UNFILLED: {', '.join(t.unfilled_slots)}")

        if report.total_data_loss_events > 0:
            print("\n  Data Loss Events:")
            for stage in report.stages:
                for ev in stage.data_loss:
                    print(f"    [{ev.stage}] {ev.type}: {ev.detail}")

    print(f"\n  Output directory: {out}")
    return out


def _print_tree_summary(structure: DesignFileStructure) -> None:
    """Print a compact summary of the parsed node tree."""
    from app.design_sync.protocol import DesignNode

    type_counts: dict[str, int] = {}
    max_depth = 0
    total = 0

    def _walk(node: DesignNode, depth: int = 0) -> None:
        nonlocal max_depth, total
        total += 1
        max_depth = max(max_depth, depth)
        type_counts[node.type.value] = type_counts.get(node.type.value, 0) + 1
        for child in node.children:
            _walk(child, depth + 1)

    for page in structure.pages:
        _walk(page)

    print(f"\n  Node tree: {total} nodes, max depth {max_depth}")
    print(f"  Types: {dict(sorted(type_counts.items(), key=lambda x: -x[1]))}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.design_sync.diagnose.extract",
        description="Extract Figma API JSON + run conversion diagnostics.",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--connection-id",
        type=int,
        help="DB connection ID (decrypts stored Figma token)",
    )
    source.add_argument(
        "--figma-url",
        type=str,
        help="Figma file URL (reads FIGMA_TOKEN env var)",
    )

    parser.add_argument(
        "--node-id",
        type=str,
        help="Specific frame node ID to extract (e.g., 2833-1623). "
        "Smaller and faster than extracting the full file.",
    )
    parser.add_argument(
        "--list-frames",
        action="store_true",
        help="List top-level frames in the file (to find email node-ids)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Output directory (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--no-diagnostics",
        action="store_true",
        help="Skip running the diagnostic pipeline (just dump raw + parsed JSON)",
    )
    return parser


async def _async_main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Resolve credentials
    if args.connection_id:
        file_key, token = await _get_connection_creds(args.connection_id)
        label = str(args.connection_id)
    else:
        file_key = _extract_file_key(args.figma_url)
        token = os.environ.get("FIGMA_TOKEN", "")
        if not token:
            print("ERROR: Set FIGMA_TOKEN env var or use --connection-id.", file=sys.stderr)
            sys.exit(1)
        label = file_key[:12]

    if args.list_frames:
        await list_frames(file_key, token)
        return

    await extract(
        file_key,
        token,
        node_id=args.node_id,
        output_dir=args.output_dir,
        label=label,
        run_diagnostics=not args.no_diagnostics,
    )


def main(argv: list[str] | None = None) -> None:
    """Synchronous entry point."""
    asyncio.run(_async_main(argv))


if __name__ == "__main__":
    main()
