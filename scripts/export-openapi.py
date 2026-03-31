#!/usr/bin/env python3
"""Export OpenAPI spec from FastAPI app without running the server.

Usage:
    uv run python scripts/export-openapi.py
    uv run python scripts/export-openapi.py --output path/to/openapi.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow importing app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export OpenAPI spec from FastAPI app",
    )
    parser.add_argument(
        "--output",
        default="cms/packages/sdk/openapi.json",
        help="Output path (default: cms/packages/sdk/openapi.json)",
    )
    args = parser.parse_args()

    from app.main import app

    spec = app.openapi()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"OpenAPI spec written to {output} ({len(spec.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
