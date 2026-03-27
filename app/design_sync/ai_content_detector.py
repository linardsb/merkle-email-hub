"""Semantic content role detection — heuristic first, LLM fallback.

Detects content roles (logo, social_links, unsubscribe_link, legal_text, etc.)
from section text/structure rather than relying on naming conventions.
Heuristic pass is free and handles most cases; LLM is called only for sections
where heuristics found nothing AND section type is UNKNOWN.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.design_sync.figma.layout_analyzer import EmailSection

logger = get_logger(__name__)

ContentRole = Literal[
    "logo",
    "social_links",
    "unsubscribe_link",
    "legal_text",
    "navigation",
    "preheader",
    "view_in_browser",
    "address",
]

_ALL_CONTENT_ROLES: frozenset[str] = frozenset(
    {
        "logo",
        "social_links",
        "unsubscribe_link",
        "legal_text",
        "navigation",
        "preheader",
        "view_in_browser",
        "address",
    }
)

_UNSUBSCRIBE_RE = re.compile(r"\bunsubscribe\b", re.IGNORECASE)
_LEGAL_RE = re.compile(r"\u00a9|copyright|\ball rights reserved\b", re.IGNORECASE)
_VIEW_BROWSER_RE = re.compile(
    r"\bview (?:in |on )?(?:your )?browser\b|\bview online\b", re.IGNORECASE
)
_SOCIAL_URL_RE = re.compile(
    r"(?:facebook|twitter|x|instagram|linkedin|youtube|tiktok|pinterest)\.com",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(
    r"\d+\s+\w+\s+(?:st(?:reet)?|ave(?:nue)?|blvd|rd|dr|ln|way|ct)\b",
    re.IGNORECASE,
)

# Cache: content hash -> roles (bounded to prevent unbounded growth)
_CACHE_MAX_SIZE = 1024
_role_cache: dict[str, tuple[str, ...]] = {}


@dataclass(frozen=True)
class ContentRoleAnnotation:
    """Detected content roles for a section."""

    section_node_id: str
    roles: tuple[str, ...]
    source: Literal["heuristic", "llm"]


def _content_hash(section: EmailSection) -> str:
    """Hash section text content for caching."""
    text = "|".join(t.content[:100] for t in section.texts[:10])
    img_info = f"|imgs={len(section.images)}"
    return hashlib.sha256((text + img_info).encode()).hexdigest()[:16]


def _detect_heuristic(section: EmailSection, section_index: int, _total: int) -> list[str]:
    """Detect content roles using regex/structural heuristics (no LLM)."""
    roles: list[str] = []
    all_text = " ".join(t.content for t in section.texts)

    # Unsubscribe link
    if _UNSUBSCRIBE_RE.search(all_text):
        roles.append("unsubscribe_link")

    # Legal text (©, copyright, all rights reserved)
    if _LEGAL_RE.search(all_text):
        roles.append("legal_text")

    # View in browser
    if _VIEW_BROWSER_RE.search(all_text):
        roles.append("view_in_browser")

    # Social links (URLs to social platforms)
    if _SOCIAL_URL_RE.search(all_text):
        roles.append("social_links")

    # Address pattern
    if _ADDRESS_RE.search(all_text):
        roles.append("address")

    # Logo: first section, single small image, minimal text
    if section_index == 0 and len(section.images) == 1 and len(section.texts) <= 1:
        img = section.images[0]
        if img.height is not None and img.height < 100:
            roles.append("logo")

    # Navigation: 4+ short text blocks
    if len(section.texts) >= 4 and all(len(t.content) < 30 for t in section.texts):
        roles.append("navigation")

    # Preheader: first section, single short text, small font
    if section_index == 0 and len(section.texts) == 1 and not section.images:
        t = section.texts[0]
        if len(t.content) < 200 and (t.font_size is None or t.font_size <= 13):
            roles.append("preheader")

    return roles


def _build_role_prompt(section: EmailSection, section_index: int, total: int) -> str:
    """Build a compact prompt for LLM content role detection."""
    lines = [
        'Detect content roles in this email section. Respond with JSON: {"roles": [...]}',
        f"Valid roles: {sorted(_ALL_CONTENT_ROLES)}",
        "",
        f"Section {section_index + 1} of {total}:",
    ]

    if section.texts:
        lines.append("  Texts:")
        for t in section.texts[:5]:
            snippet = t.content[:100]
            size_info = f" (size={t.font_size})" if t.font_size else ""
            lines.append(f'    - "{snippet}"{size_info}')

    if section.images:
        lines.append(f"  Images: {len(section.images)}")
        for img in section.images[:3]:
            lines.append(f"    - {img.width}x{img.height}")

    if section.buttons:
        lines.append(f"  Buttons: {len(section.buttons)}")

    return "\n".join(lines)


def _parse_roles(raw: str) -> list[str]:
    """Parse LLM JSON response into a list of valid ContentRole strings."""
    try:
        data: dict[str, object] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []

    raw_roles: object = data.get("roles", [])
    if not isinstance(raw_roles, list):
        return []

    result: list[str] = []
    for entry in raw_roles:  # pyright: ignore[reportUnknownVariableType]
        if isinstance(entry, str) and entry in _ALL_CONTENT_ROLES:
            result.append(entry)
    return result


async def detect_content_roles(
    sections: list[EmailSection],
) -> list[ContentRoleAnnotation]:
    """Detect semantic content roles for all sections.

    Two-pass approach:
    1. Heuristic pass (free, fast) — regex and structural patterns
    2. LLM pass (only for UNKNOWN sections with no heuristic matches)

    Args:
        sections: All sections from layout analysis.

    Returns:
        Annotations in the same order as input sections.
    """
    from app.design_sync.figma.layout_analyzer import EmailSectionType

    total = len(sections)
    annotations: list[ContentRoleAnnotation] = []
    llm_needed: list[tuple[int, EmailSection]] = []

    # Pass 1: heuristic detection
    for idx, section in enumerate(sections):
        h = _content_hash(section)
        if h in _role_cache:
            annotations.append(
                ContentRoleAnnotation(
                    section_node_id=section.node_id,
                    roles=_role_cache[h],
                    source="heuristic",
                )
            )
            continue

        roles = _detect_heuristic(section, idx, total)
        if roles:
            role_tuple = tuple(sorted(set(roles)))
            if len(_role_cache) >= _CACHE_MAX_SIZE:
                _role_cache.clear()
            _role_cache[h] = role_tuple
            annotations.append(
                ContentRoleAnnotation(
                    section_node_id=section.node_id,
                    roles=role_tuple,
                    source="heuristic",
                )
            )
        elif section.section_type == EmailSectionType.UNKNOWN and section.texts:
            # No heuristic match + UNKNOWN type + has text → candidate for LLM
            annotations.append(
                ContentRoleAnnotation(
                    section_node_id=section.node_id,
                    roles=(),
                    source="heuristic",
                )
            )
            llm_needed.append((len(annotations) - 1, section))
        else:
            annotations.append(
                ContentRoleAnnotation(
                    section_node_id=section.node_id,
                    roles=(),
                    source="heuristic",
                )
            )

    # Pass 2: LLM fallback for undetected UNKNOWN sections
    if llm_needed:
        from app.ai.protocols import Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model

        model = resolve_model("lightweight")
        registry = get_registry()
        provider = registry.get_llm(model)

        for ann_idx, section in llm_needed:
            section_index = next(
                (i for i, s in enumerate(sections) if s.node_id == section.node_id),
                0,
            )
            prompt = _build_role_prompt(section, section_index, total)

            try:
                response = await provider.complete(
                    [Message(role="user", content=prompt)],
                    model=model,
                )
                roles = _parse_roles(response.content)
                role_tuple = tuple(sorted(set(roles)))

                h = _content_hash(section)
                if len(_role_cache) >= _CACHE_MAX_SIZE:
                    _role_cache.clear()
                _role_cache[h] = role_tuple

                annotations[ann_idx] = ContentRoleAnnotation(
                    section_node_id=section.node_id,
                    roles=role_tuple,
                    source="llm",
                )
                logger.info(
                    "design_sync.content_detector.llm_detected",
                    node_id=section.node_id,
                    roles=role_tuple,
                )
            except Exception:
                logger.warning(
                    "design_sync.content_detector.llm_error",
                    node_id=section.node_id,
                    exc_info=True,
                )

    return annotations


def clear_cache() -> None:
    """Clear the role detection cache (for testing)."""
    _role_cache.clear()
