"""Load component seeds from YAML manifest and HTML files on disk."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.components.data.compatibility_presets import resolve_compatibility
from app.core.logging import get_logger

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = Path(__file__).resolve().parent / "component_manifest.yaml"

_REQUIRED_FIELDS = {"slug", "name", "description", "category", "compatibility"}

_DATA_SLOT_RE = re.compile(r'data-slot="([^"]+)"')


def _extract_slots_from_html(html_source: str) -> list[dict[str, Any]]:
    """Auto-detect slot definitions from ``data-slot`` attributes in HTML.

    Returns a list of slot dicts as fallback when the manifest entry
    has no ``slot_definitions``.  Operates on trusted, repo-committed
    HTML — no user input.
    """
    seen: set[str] = set()
    slots: list[dict[str, Any]] = []
    for match in _DATA_SLOT_RE.finditer(html_source):
        slot_id = match.group(1)
        if slot_id in seen:
            continue
        seen.add(slot_id)
        slots.append(
            {
                "slot_id": slot_id,
                "slot_type": "content",
                "selector": f"[data-slot='{slot_id}']",
                "required": False,
            }
        )
    return slots


@lru_cache(maxsize=1)
def _load_manifest() -> tuple[dict[str, Any], ...]:
    """Parse the YAML manifest and load HTML for each component.

    Returns an immutable tuple for caching. Callers convert to list.
    """
    with _MANIFEST_PATH.open() as f:
        data = yaml.safe_load(f)

    html_dir = _REPO_ROOT / data.get("html_dir", "email-templates/components")
    entries: list[dict[str, Any]] = data.get("components", [])

    seen_slugs: set[str] = set()
    results: list[dict[str, Any]] = []

    for entry in entries:
        # Validate required fields
        missing = _REQUIRED_FIELDS - set(entry)
        if missing:
            msg = f"Manifest entry missing required fields {missing}: {entry}"
            raise ValueError(msg)

        slug = entry["slug"]

        # Check for duplicate slugs within the manifest
        if slug in seen_slugs:
            msg = f"Duplicate slug in manifest: {slug!r}"
            raise ValueError(msg)
        seen_slugs.add(slug)

        # Resolve HTML file
        filename = entry.get("file", f"{slug}.html")
        html_path = html_dir / filename
        if not html_path.is_file():
            logger.warning(
                "component_manifest.file_missing",
                slug=slug,
                path=str(html_path),
            )
            continue

        html_source = html_path.read_text(encoding="utf-8")

        slot_definitions = entry.get("slot_definitions")
        if not slot_definitions:
            slot_definitions = _extract_slots_from_html(html_source)

        results.append(
            {
                "name": entry["name"],
                "slug": slug,
                "description": entry["description"],
                "category": entry["category"],
                "html_source": html_source,
                "css_source": entry.get("css_source"),
                "compatibility": resolve_compatibility(entry["compatibility"]),
                "slot_definitions": slot_definitions,
                "default_tokens": entry.get("default_tokens"),
                "inject_target": entry.get("inject_target", "body"),
            }
        )

    logger.info(
        "component_manifest.loaded",
        count=len(results),
        skipped=len(entries) - len(results),
    )
    return tuple(results)


def load_file_components() -> list[dict[str, Any]]:
    """Load file-based component seeds from the YAML manifest.

    Each component's HTML is read from the corresponding file in
    ``email-templates/components/``. Components with missing HTML
    files are logged and skipped.
    """
    return list(_load_manifest())
