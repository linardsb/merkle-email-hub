"""CLI entry point: python -m app.design_sync.diagnose."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.design_sync.diagnose.report import (
    dump_structure_to_json,
    dump_tokens_to_json,
    load_structure_from_json,
    load_tokens_from_json,
    report_to_json,
)
from app.design_sync.diagnose.runner import DiagnosticRunner
from app.design_sync.protocol import ExtractedTokens


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.design_sync.diagnose",
        description="Run conversion diagnostics on a design file structure.",
    )
    parser.add_argument(
        "--structure-json",
        type=Path,
        help="Cached DesignFileStructure JSON (from dump_structure)",
    )
    parser.add_argument(
        "--tokens-json",
        type=Path,
        help="Cached ExtractedTokens JSON (optional, defaults to empty)",
    )
    parser.add_argument(
        "--raw-figma-json",
        type=Path,
        help="Raw Figma API response (for IMAGE fill detection)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--dump-structure",
        type=Path,
        help="Dump the structure JSON for future offline use",
    )
    parser.add_argument(
        "--dump-tokens",
        type=Path,
        help="Dump the tokens JSON for future offline use",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the diagnostic pipeline from the command line."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.structure_json:
        parser.error(
            "--structure-json is required. To extract from Figma, use:\n"
            "  python -m app.design_sync.diagnose.extract --connection-id <ID> --node-id <NODE>"
        )

    # Load structure
    structure = load_structure_from_json(args.structure_json)

    # Load tokens (optional)
    tokens = ExtractedTokens()
    if args.tokens_json:
        tokens = load_tokens_from_json(args.tokens_json)

    # Load raw Figma JSON (optional)
    raw_figma_json = None
    if args.raw_figma_json:
        raw_figma_json = json.loads(args.raw_figma_json.read_text())

    # Dump structure/tokens if requested
    if args.dump_structure:
        dump_structure_to_json(structure, args.dump_structure)

    if args.dump_tokens:
        dump_tokens_to_json(tokens, args.dump_tokens)

    # Run diagnostics
    runner = DiagnosticRunner()
    report = runner.run_from_structure(
        structure,
        tokens,
        raw_figma_json=raw_figma_json,
    )

    # Output
    output_json = report_to_json(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_json)
    else:
        sys.stdout.write(output_json + "\n")


if __name__ == "__main__":
    main()
