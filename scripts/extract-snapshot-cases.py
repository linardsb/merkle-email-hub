#!/usr/bin/env python3
"""Extract Figma data for snapshot regression test cases 6 and 10.

Usage:
    FIGMA_TOKEN=figd_xxx python scripts/extract-snapshot-cases.py

Fetches node subtrees from Figma API for:
  - Case 6: Starbucks Pumpkin Spice (node 2833-1424)
  - Case 10: Mammut Duvet Day (node 2833-1135)

Then parses each into structure.json + tokens.json using the same
pipeline as `python -m app.design_sync.diagnose.extract`.

Case 5 (MAAP x KASK, node 2833-1623) already has data in data/debug/5/.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FILE_KEY = "VUlWjZGAEVZr3mK1EawsYR"
FIGMA_API = "https://api.figma.com"

CASES = [
    {"id": "6", "node_id": "2833-1424", "name": "Starbucks Pumpkin Spice"},
    {"id": "10", "node_id": "2833-1135", "name": "Mammut Duvet Day"},
]


async def fetch_and_parse(token: str, case: dict[str, str], debug_dir: Path) -> None:
    """Fetch a single node from Figma and parse into structure + tokens."""
    import httpx

    from app.design_sync.diagnose.report import (
        dump_structure_to_json,
        dump_tokens_to_json,
        load_tokens_from_json,
    )
    from app.design_sync.figma.service import FigmaDesignSyncService
    from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType

    case_dir = debug_dir / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    node_id = case["node_id"]
    figma_node_id = node_id.replace("-", ":")

    print(f"\n{'=' * 60}")
    print(f"Case {case['id']}: {case['name']} (node {node_id})")
    print(f"{'=' * 60}")

    # 1. Fetch from Figma API
    print(f"  Fetching node {node_id} from Figma API...")
    headers = {"X-Figma-Token": token}
    async with httpx.AsyncClient(timeout=60.0) as client:
        url = f"{FIGMA_API}/v1/files/{FILE_KEY}/nodes"
        resp = await client.get(url, headers=headers, params={"ids": figma_node_id})
        if resp.status_code == 403:
            print("  ERROR: Figma token is invalid or expired.")
            sys.exit(1)
        resp.raise_for_status()
        raw = resp.json()

    # Save raw JSON
    raw_path = case_dir / "raw_figma.json"
    raw_path.write_text(json.dumps(raw, indent=2))
    print(f"  Saved raw JSON: {raw_path} ({raw_path.stat().st_size:,} bytes)")

    # 2. Parse into DesignFileStructure
    service = FigmaDesignSyncService()
    node_data = raw["nodes"].get(figma_node_id, {})
    doc = node_data.get("document", {})
    parsed_node = service._parse_node(doc, current_depth=0, max_depth=None)

    page = DesignNode(
        id="0:1",
        name="Email",
        type=DesignNodeType.PAGE,
        children=[parsed_node],
    )
    structure = DesignFileStructure(
        file_name=raw.get("name", "Untitled"),
        pages=[page],
    )

    dump_structure_to_json(structure, case_dir / "structure.json")
    print(f"  Saved structure.json ({(case_dir / 'structure.json').stat().st_size:,} bytes)")

    # 3. Tokens — try cached from case 5, else fetch full file
    case5_tokens = debug_dir / "5" / "tokens.json"
    if case5_tokens.exists():
        print("  Reusing tokens from case 5 (same Figma file)...")
        tokens = load_tokens_from_json(case5_tokens)
    else:
        print("  No cached tokens — fetching full file for token extraction...")
        tokens, _ = await service.sync_tokens_and_structure(FILE_KEY, token)

    dump_tokens_to_json(tokens, case_dir / "tokens.json")
    print(f"  Saved tokens.json ({(case_dir / 'tokens.json').stat().st_size:,} bytes)")

    # 4. Summary
    node_count = _count_nodes([parsed_node])
    print(
        f"  Nodes: {node_count}, Colors: {len(tokens.colors)}, Typography: {len(tokens.typography)}"
    )
    print(f"  Done: {case_dir}")


def _count_nodes(nodes: list) -> int:  # type: ignore[type-arg]
    count = 0
    for n in nodes:
        count += 1
        count += _count_nodes(getattr(n, "children", []) or [])
    return count


async def main() -> None:
    token = os.environ.get("FIGMA_TOKEN", "")
    if not token:
        print("ERROR: Set FIGMA_TOKEN env var.")
        print("  FIGMA_TOKEN=figd_xxx python scripts/extract-snapshot-cases.py")
        sys.exit(1)

    debug_dir = Path(__file__).resolve().parents[1] / "data" / "debug"

    for case in CASES:
        case_dir = debug_dir / case["id"]
        if (case_dir / "structure.json").exists() and (case_dir / "tokens.json").exists():
            print(f"Case {case['id']} already has data — skipping (delete to re-extract)")
            continue
        await fetch_and_parse(token, case, debug_dir)

    print("\n\nAll cases extracted. Next steps:")
    print("  1. Copy reference HTMLs:")
    print(
        "     cp email-templates/training_HTML/for_converter_engine/starbucks-pumpkin-spice.html data/debug/6/expected.html"
    )
    print(
        "     cp email-templates/training_HTML/for_converter_engine/mammut-duvet-day.html data/debug/10/expected.html"
    )
    print("  2. Run: make snapshot-test")


if __name__ == "__main__":
    asyncio.run(main())
