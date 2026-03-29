"""Generate DATA JSON for the eval labeling tool from traces + labels JSONL files.

Usage:
    python scripts/generate-labeling-data.py --traces-dir traces/ --output docs/eval-labeling-data.json
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
    """Load a JSONL file, returning list of dicts."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw_line in path.read_text().strip().splitlines():
        raw_line = raw_line.strip()
        if raw_line:
            rows.append(json.loads(raw_line))
    return rows


def build_data(traces_dir: Path) -> dict[str, Any]:
    """Build the DATA structure for the labeling tool."""
    data: dict[str, Any] = {"traces": {}, "labels": {}, "verdict_comparison": {}}

    # Load verdict comparison if it exists
    vc_path = traces_dir / "verdict_comparison.json"
    if vc_path.exists():
        data["verdict_comparison"] = json.loads(vc_path.read_text())

    for agent in AGENTS:
        # Load traces
        traces = load_jsonl(traces_dir / f"{agent}_traces.jsonl")
        trace_list: list[dict[str, Any]] = []
        for t in traces:
            trace_list.append(
                {
                    "id": t.get("trace_id", t.get("id", "")),
                    "agent": agent,
                    "dimensions": t.get("dimensions", {}),
                    "input": t.get("input", {}),
                    "output": t.get("output", {}),
                    "expected_challenges": t.get("expected_challenges", []),
                }
            )
        data["traces"][agent] = trace_list

        # Load labels (with judge verdicts pre-filled)
        labels = load_jsonl(traces_dir / f"{agent}_human_labels.jsonl")
        data["labels"][agent] = labels

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate labeling tool data")
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=Path("traces"),
        help="Directory containing traces and labels JSONL files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/eval-labeling-data.json"),
        help="Output JSON file path",
    )
    args = parser.parse_args()

    data = build_data(args.traces_dir)

    labels_dict: dict[str, list[dict[str, Any]]] = data["labels"]
    traces_dict: dict[str, list[dict[str, Any]]] = data["traces"]
    total_labels = sum(len(v) for v in labels_dict.values())
    total_traces = sum(len(v) for v in traces_dict.values())

    args.output.write_text(json.dumps(data))
    print(
        f"Generated {args.output}: {total_traces} traces, {total_labels} labels across {len(AGENTS)} agents"
    )


if __name__ == "__main__":
    main()
