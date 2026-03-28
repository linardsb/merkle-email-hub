"""Infer email section types from position and content heuristics."""

from __future__ import annotations

from dataclasses import replace

from app.design_sync.email_design_document import DocumentSection

# Sections with these types were already assigned by the parser
_EXPLICIT_TYPES = frozenset({"hero", "social", "nav", "spacer", "divider"})

_SMALL_FONT_THRESHOLD = 14.0


def infer_section_types(sections: list[DocumentSection]) -> list[DocumentSection]:
    """Assign section types based on position + content heuristics.

    Only modifies sections whose ``type`` is ``"unknown"``.
    """
    if not sections:
        return sections

    result: list[DocumentSection] = list(sections)

    for idx, section in enumerate(result):
        if section.type in _EXPLICIT_TYPES:
            continue
        if section.type != "unknown":
            continue

        inferred = _infer_single(section, idx, len(result))
        if inferred != section.type:
            result[idx] = replace(section, type=inferred)

    return result


def _infer_single(section: DocumentSection, idx: int, total: int) -> str:
    # First section with image(s) and no text → HEADER
    if idx == 0 and section.images and not section.texts:
        return "header"

    # Last section with small text or social content roles → FOOTER
    if idx == total - 1:
        if _has_small_text(section):
            return "footer"
        if any(r in ("legal_text", "unsubscribe_link") for r in section.content_roles):
            return "footer"

    # Section with only button(s) and no images → CTA
    if section.buttons and not section.images:
        has_only_short_text = all(len(t.content) < 100 for t in section.texts)
        if not section.texts or has_only_short_text:
            return "cta"

    # Section with background image + heading → HERO
    bg_images = [i for i in section.images if i.is_background]
    headings = [t for t in section.texts if t.is_heading]
    if bg_images and headings:
        return "hero"

    return "content"


def _has_small_text(section: DocumentSection) -> bool:
    if not section.texts:
        return False
    return all(
        (t.font_size is not None and t.font_size < _SMALL_FONT_THRESHOLD) for t in section.texts
    )
