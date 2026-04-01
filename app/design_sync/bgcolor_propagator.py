"""Adjacent-section background color propagation for visual continuity (Phase 41.2).

When a full-width-image section is adjacent to a text/heading/CTA section,
sample the facing edge of the image. If a solid color is detected, inject
``bgcolor`` on the adjacent content section's outermost ``<table>``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from app.core.logging import get_logger
from app.design_sync.image_sampler import sample_edge_color

if TYPE_CHECKING:
    from app.design_sync.component_matcher import ComponentMatch

logger = get_logger(__name__)

# Component slugs that receive propagated bgcolor
_TEXT_LIKE_SLUGS: frozenset[str] = frozenset(
    {
        "text-block",
        "heading-block",
        "hero-text",
        "hero-block",
        "cta-button",
        "article-card",
        "button-block",
        "text-link",
        "product-card",
        "category-nav",
    }
)

# Regex to match the first <table ...> opening tag in section HTML
_FIRST_TABLE_RE = re.compile(r"(<table\b)([^>]*)(>)", re.IGNORECASE)


def propagate_adjacent_bgcolor(
    matches: list[ComponentMatch],
    rendered_parts: list[str],
    *,
    connection_id: str | None = None,
    image_dir: Path | None = None,
) -> list[str]:
    """Scan adjacent (image, text) pairs and propagate edge color as bgcolor.

    Args:
        matches: Ordered ComponentMatch objects (one per section).
        rendered_parts: Parallel HTML strings (may include interleaved spacers).
        connection_id: Design connection ID for resolving local asset paths.
        image_dir: Override directory for image assets (useful in tests).

    Returns:
        Copy of *rendered_parts* with ``bgcolor`` injected where applicable.
    """
    if len(matches) < 2:
        return rendered_parts

    asset_dir = _resolve_asset_dir(connection_id, image_dir)
    if asset_dir is None:
        return rendered_parts

    result = list(rendered_parts)
    part_indices = _build_part_index(matches, result)

    for i in range(len(matches) - 1):
        m_curr = matches[i]
        m_next = matches[i + 1]

        # Image above → text below: sample bottom edge
        if (
            m_curr.component_slug == "full-width-image"
            and m_next.component_slug in _TEXT_LIKE_SLUGS
        ):
            color = _sample_edge(m_curr, asset_dir, "bottom")
            if color:
                idx = part_indices.get(i + 1)
                if idx is not None:
                    result[idx] = _inject_bgcolor(result[idx], color)
                    logger.info(
                        "design_sync.bgcolor_propagated",
                        source_section=m_curr.section_idx,
                        target_section=m_next.section_idx,
                        color=color,
                        direction="down",
                    )

        # Text above → image below: sample top edge
        if (
            m_next.component_slug == "full-width-image"
            and m_curr.component_slug in _TEXT_LIKE_SLUGS
        ):
            color = _sample_edge(m_next, asset_dir, "top")
            if color:
                idx = part_indices.get(i)
                if idx is not None:
                    result[idx] = _inject_bgcolor(result[idx], color)
                    logger.info(
                        "design_sync.bgcolor_propagated",
                        source_section=m_next.section_idx,
                        target_section=m_curr.section_idx,
                        color=color,
                        direction="up",
                    )

    return result


def _resolve_asset_dir(
    connection_id: str | None,
    image_dir: Path | None,
) -> Path | None:
    """Resolve the directory containing downloaded image assets."""
    if image_dir is not None:
        return image_dir
    if connection_id is None:
        return None
    from app.core.config import get_settings

    path = Path(get_settings().design_sync.asset_storage_path) / str(connection_id)
    if path.is_dir():
        return path
    return None


def _sanitize_node_id(node_id: str) -> str:
    """Convert Figma node ID (e.g. '1:2') to filesystem-safe string ('1_2')."""
    return node_id.replace(":", "_")


def _get_image_path(match: ComponentMatch, asset_dir: Path) -> Path | None:
    """Get local file path for the first image in a section."""
    if not match.section.images:
        return None
    node_id = match.section.images[0].node_id
    safe_id = _sanitize_node_id(node_id)
    for ext in ("png", "jpg", "jpeg"):
        path = asset_dir / f"{safe_id}.{ext}"
        if path.is_file():
            return path
    return None


def _sample_edge(
    match: ComponentMatch,
    asset_dir: Path,
    edge: Literal["top", "bottom"],
) -> str | None:
    """Sample the specified edge of the first image in a section."""
    path = _get_image_path(match, asset_dir)
    if path is None:
        return None
    return sample_edge_color(path, edge)


def _build_part_index(
    matches: list[ComponentMatch],
    parts: list[str],
) -> dict[int, int]:
    """Map match index → rendered_parts index.

    ``rendered_parts`` interleaves section HTML with optional MSO spacer
    blocks.  Spacers start with ``<!--[if mso]>`` whereas real section
    HTML starts with ``<table``, so we distinguish by the leading content.
    """
    index: dict[int, int] = {}
    match_idx = 0
    for part_idx, part in enumerate(parts):
        # Spacers start with the MSO conditional comment; section HTML
        # starts with <table (possibly after whitespace).
        stripped = part.lstrip()
        if stripped.startswith("<!--[if mso]>"):
            continue
        if match_idx < len(matches):
            index[match_idx] = part_idx
            match_idx += 1
    return index


def _inject_bgcolor(html: str, color: str) -> str:
    """Inject ``bgcolor`` on the first ``<table>`` that lacks one."""

    def _replace(m: re.Match[str]) -> str:
        tag_start = m.group(1)
        attrs = m.group(2)
        tag_end = m.group(3)
        if "bgcolor" in attrs.lower():
            return m.group(0)
        return f'{tag_start} bgcolor="{color}"{attrs}{tag_end}'

    return _FIRST_TABLE_RE.sub(_replace, html, count=1)
