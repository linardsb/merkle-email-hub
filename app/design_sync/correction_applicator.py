"""Deterministic correction applicator for VLM-identified HTML mismatches.

Phase 47.3: Applies SectionCorrection items from visual_verify (47.2) by
splicing inline style / content / image attribute changes into section HTML.
Complex layout restructuring is skipped (caller delegates to LLM fallback).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lxml import html as lxml_html
from lxml.cssselect import CSSSelector

from app.core.logging import get_logger
from app.design_sync.visual_verify import SectionCorrection

if TYPE_CHECKING:
    from lxml.html import HtmlElement

logger = get_logger(__name__)

_SECTION_RE = re.compile(r"<!--\s*section:(\S+)\s*-->")

_UNSAFE_CSS_RE = re.compile(
    r"expression\s*\(|url\s*\(\s*javascript\s*:|url\s*\(\s*data\s*:\s*text/html"
    r"|-moz-binding\s*:|@import",
    re.IGNORECASE,
)

_STYLE_PROP_TYPES: frozenset[str] = frozenset({"color", "font", "spacing"})

_LAYOUT_SIMPLE_PROPS: frozenset[str] = frozenset(
    {"width", "max-width", "min-width", "text-align", "vertical-align"},
)


@dataclass(frozen=True)
class CorrectionResult:
    """Outcome of deterministic correction application."""

    html: str
    applied: list[SectionCorrection] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    skipped: list[SectionCorrection] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]


# ---------------------------------------------------------------------------
# CSS value sanitisation
# ---------------------------------------------------------------------------


def _sanitize_css_value(value: str) -> str:
    """Strip dangerous CSS patterns; return empty string if entirely unsafe."""
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    sanitized = _UNSAFE_CSS_RE.sub("", sanitized)
    sanitized = re.sub(r'[;<>{}\'"\\]+', "", sanitized)
    return sanitized.strip()


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------


def _extract_section_html(html: str, node_id: str) -> tuple[int, int] | None:
    """Return (start, end) char offsets for the section matching *node_id*.

    Sections are delimited by consecutive ``<!-- section:ID -->`` markers.
    The last section extends to ``</body>`` or end-of-string.
    """
    markers: list[tuple[int, int, str]] = []  # (match_start, match_end, id)
    for m in _SECTION_RE.finditer(html):
        markers.append((m.start(), m.end(), m.group(1)))

    target_idx: int | None = None
    for i, (_ms, _me, mid) in enumerate(markers):
        # Prefix match: node_id "hero_1" matches marker "hero_1:content"
        if mid == node_id or mid.startswith(node_id + ":"):
            target_idx = i
            break

    if target_idx is None:
        return None

    section_start = markers[target_idx][1]  # after the marker comment

    if target_idx + 1 < len(markers):
        section_end = markers[target_idx + 1][0]
    else:
        # Last section: extend to </body> or end of string
        body_close = html.find("</body>", section_start)
        section_end = body_close if body_close != -1 else len(html)

    return (section_start, section_end)


# ---------------------------------------------------------------------------
# lxml fragment helpers
# ---------------------------------------------------------------------------


def _parse_fragment(section_html: str) -> HtmlElement:
    """Parse an HTML fragment, returning the root element."""
    doc: HtmlElement = lxml_html.fragment_fromstring(section_html, create_parent="div")
    return doc


def _serialize_fragment(root: HtmlElement) -> str:
    """Serialize an lxml fragment back to an HTML string (no wrapper div)."""
    raw = lxml_html.tostring(root, encoding="unicode")
    # Strip the synthetic <div>…</div> wrapper added by fragment_fromstring
    if raw.startswith("<div>") and raw.endswith("</div>"):
        return raw[5:-6]
    return raw


# ---------------------------------------------------------------------------
# Style string helpers
# ---------------------------------------------------------------------------


def _parse_inline_style(style: str) -> dict[str, str]:
    """Parse ``style`` attribute into ``{property: value}`` dict."""
    result: dict[str, str] = {}
    for part in style.split(";"):
        part = part.strip()
        if ":" not in part:
            continue
        prop, _, val = part.partition(":")
        result[prop.strip().lower()] = val.strip()
    return result


def _serialize_inline_style(styles: dict[str, str]) -> str:
    """Serialize style dict back to inline attribute value."""
    return "; ".join(f"{k}: {v}" for k, v in styles.items())


# ---------------------------------------------------------------------------
# Per-type correction handlers
# ---------------------------------------------------------------------------


def _apply_style_correction(
    section_html: str,
    correction: SectionCorrection,
) -> str | None:
    """Replace a CSS property value in the matched element's inline style.

    Returns modified section HTML, or ``None`` if element/property not found.
    """
    if (
        correction.correction_type == "layout"
        and correction.css_property.lower() not in _LAYOUT_SIMPLE_PROPS
    ):
        return None  # complex layout — skip for LLM fallback

    safe_value = _sanitize_css_value(correction.correct_value)
    if not safe_value:
        logger.warning(
            "correction.unsafe_css_value",
            node_id=correction.node_id,
            css_property=correction.css_property,
        )
        return None

    root = _parse_fragment(section_html)

    try:
        selector = CSSSelector(correction.css_selector)
    except Exception:
        logger.warning(
            "correction.invalid_css_selector",
            selector=correction.css_selector,
            node_id=correction.node_id,
        )
        return None

    elements: list[HtmlElement] = selector(root)
    if not elements:
        return None

    modified = False
    prop_name = correction.css_property.lower()
    for el in elements:
        style_attr = el.get("style", "")
        styles = _parse_inline_style(style_attr)
        if prop_name in styles:
            styles[prop_name] = safe_value
            el.set("style", _serialize_inline_style(styles))
            modified = True

    return _serialize_fragment(root) if modified else None


def _apply_content_correction(
    section_html: str,
    correction: SectionCorrection,
) -> str | None:
    """Replace text content of the matched element."""
    root = _parse_fragment(section_html)

    try:
        selector = CSSSelector(correction.css_selector)
    except Exception:
        return None

    elements: list[HtmlElement] = selector(root)
    if not elements:
        return None

    target = elements[0]
    if target.text is None and correction.current_value:
        return None

    target.text = correction.correct_value
    return _serialize_fragment(root)


def _apply_image_correction(
    section_html: str,
    correction: SectionCorrection,
) -> str | None:
    """Replace width/height on a matched ``<img>`` element."""
    root = _parse_fragment(section_html)

    try:
        selector = CSSSelector(correction.css_selector)
    except Exception:
        return None

    elements: list[HtmlElement] = selector(root)
    if not elements:
        return None

    prop = correction.css_property.lower()
    if prop not in ("width", "height"):
        return None

    # Validate numeric value
    numeric = re.sub(r"[^\d.]", "", correction.correct_value)
    if not numeric:
        return None

    modified = False
    for el in elements:
        if el.tag == "img":
            el.set(prop, numeric)
            # Also update inline style if present
            style_attr = el.get("style", "")
            if style_attr:
                styles = _parse_inline_style(style_attr)
                if prop in styles:
                    styles[prop] = f"{numeric}px"
                    el.set("style", _serialize_inline_style(styles))
            modified = True

    return _serialize_fragment(root) if modified else None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def apply_corrections(
    html: str,
    corrections: list[SectionCorrection],
    *,
    confidence_threshold: float = 0.0,
) -> CorrectionResult:
    """Apply VLM corrections to converter HTML deterministically.

    Corrections are applied in list order; later corrections see earlier
    modifications.  Low-confidence corrections (below *confidence_threshold*)
    are skipped.  Complex layout corrections are collected in ``skipped`` for
    optional LLM fallback (not called here).

    This is a pure function: same input → same output, no side effects.
    """
    applied: list[SectionCorrection] = []
    skipped: list[SectionCorrection] = []

    for correction in corrections:
        # Confidence gate
        if correction.confidence < confidence_threshold:
            logger.debug(
                "correction.low_confidence",
                node_id=correction.node_id,
                confidence=correction.confidence,
                threshold=confidence_threshold,
            )
            skipped.append(correction)
            continue

        # Extract section
        bounds = _extract_section_html(html, correction.node_id)
        if bounds is None:
            logger.warning(
                "correction.section_not_found",
                node_id=correction.node_id,
            )
            skipped.append(correction)
            continue

        start, end = bounds
        section_html = html[start:end]

        # Dispatch by correction type
        ctype = correction.correction_type
        result: str | None = None

        if ctype in _STYLE_PROP_TYPES or ctype == "layout":
            result = _apply_style_correction(section_html, correction)
        elif ctype == "content":
            result = _apply_content_correction(section_html, correction)
        elif ctype == "image":
            result = _apply_image_correction(section_html, correction)

        if result is None:
            skipped.append(correction)
            continue

        # Splice modified section back into full HTML
        html = html[:start] + result + html[end:]
        applied.append(correction)

    return CorrectionResult(html=html, applied=applied, skipped=skipped)
