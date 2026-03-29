"""Golden reference loader — maps email templates to judge criteria.

Reads index.yaml from golden-references/ directory, extracts HTML snippets
(not full files) to stay within token budgets, provides query API for judges.

CLI (list references):
    python -m app.ai.agents.evals.golden_references --list
    python -m app.ai.agents.evals.golden_references --criterion mso_conditional_correctness
    python -m app.ai.agents.evals.golden_references --agent outlook_fixer
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import yaml

from app.core.exceptions import DomainValidationError, NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

_GOLDEN_REF_DIR = (
    Path(__file__).resolve().parents[4] / "email-templates" / "components" / "golden-references"
)
_INDEX_FILE = _GOLDEN_REF_DIR / "index.yaml"
_MAX_SNIPPET_LINES = 80
_MAX_SNIPPETS_PER_CRITERION = 3


@dataclass(frozen=True)
class SnippetSelector:
    """Line range for snippet extraction (1-based, inclusive)."""

    lines: tuple[int, int] | None = None


@dataclass(frozen=True)
class GoldenReference:
    """A golden reference template mapped to judge criteria."""

    name: str
    html: str
    criteria: tuple[str, ...]
    agents: tuple[str, ...]
    verified_date: str
    source_file: str


def _load_index() -> dict[str, Any]:
    """Read and validate index.yaml."""
    if not _INDEX_FILE.exists():
        msg = f"Golden reference index not found: {_INDEX_FILE}"
        raise NotFoundError(msg)
    raw: object = yaml.safe_load(_INDEX_FILE.read_text())
    if not isinstance(raw, dict) or "references" not in raw:  # pyright: ignore[reportUnknownMemberType]
        msg = "index.yaml must contain 'references' key"
        raise DomainValidationError(msg)
    return cast(dict[str, Any], raw)


def _extract_snippet(file_name: str, selector: SnippetSelector | None) -> str:
    """Extract HTML snippet from a golden reference file.

    Path traversal prevention: file_name must not contain '..' or '/'.
    """
    if ".." in file_name or "/" in file_name:
        msg = f"Invalid file name (path traversal): {file_name}"
        raise DomainValidationError(msg)
    path = _GOLDEN_REF_DIR / file_name
    if not path.exists():
        msg = f"Golden reference file not found: {file_name}"
        raise NotFoundError(msg)
    all_lines = path.read_text().splitlines()
    if selector and selector.lines:
        start, end = selector.lines
        all_lines = all_lines[max(0, start - 1) : end]
    return "\n".join(all_lines[:_MAX_SNIPPET_LINES])


@lru_cache(maxsize=1)
def load_golden_references() -> tuple[GoldenReference, ...]:
    """Load all golden references from index.yaml. Cached."""
    index = _load_index()
    refs: list[GoldenReference] = []
    for entry in index["references"]:
        selector = None
        if "selector" in entry and "lines" in entry["selector"]:
            selector = SnippetSelector(lines=tuple(entry["selector"]["lines"]))
        html = _extract_snippet(entry["file"], selector)
        refs.append(
            GoldenReference(
                name=entry["name"],
                html=html,
                criteria=tuple(entry["criteria"]),
                agents=tuple(entry["agents"]),
                verified_date=entry.get("verified", "unknown"),
                source_file=entry["file"],
            )
        )
    logger.info("golden_references.loaded", count=len(refs))
    return tuple(refs)


def get_references_for_criterion(
    criterion_name: str,
) -> list[tuple[str, str]]:
    """Return (name, html_snippet) pairs for a criterion. Max 3 snippets."""
    refs = load_golden_references()
    matches = [(r.name, r.html) for r in refs if criterion_name in r.criteria]
    return matches[:_MAX_SNIPPETS_PER_CRITERION]


def get_references_for_agent(agent_name: str) -> list[GoldenReference]:
    """Return all references relevant to an agent."""
    return [r for r in load_golden_references() if agent_name in r.agents]


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Golden reference loader CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all references")
    group.add_argument("--criterion", help="Show references for a criterion")
    group.add_argument("--agent", help="Show references for an agent")
    args = parser.parse_args()

    if args.list:
        for ref in load_golden_references():
            print(f"  {ref.name} ({ref.source_file})")  # noqa: T201
            print(f"    criteria: {', '.join(ref.criteria)}")  # noqa: T201
            print(f"    agents:   {', '.join(ref.agents)}")  # noqa: T201
            print(f"    snippet:  {len(ref.html.splitlines())} lines")  # noqa: T201
    elif args.criterion:
        results = get_references_for_criterion(args.criterion)
        if not results:
            print(f"No references for criterion: {args.criterion}")  # noqa: T201
            sys.exit(1)
        for name, html in results:
            print(f"--- {name} ---")  # noqa: T201
            print(html[:500])  # noqa: T201
    elif args.agent:
        agent_refs = get_references_for_agent(args.agent)
        if not agent_refs:
            print(f"No references for agent: {args.agent}")  # noqa: T201
            sys.exit(1)
        for ref in agent_refs:
            print(f"  {ref.name}: {', '.join(ref.criteria)}")  # noqa: T201
