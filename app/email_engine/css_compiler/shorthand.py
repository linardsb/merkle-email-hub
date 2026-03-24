"""CSS shorthand expansion utility.

Expands shorthand CSS properties (font, padding, margin, border, background)
into their longhand equivalents. Used by the compiler before ontology lookup
and independently by the token extractor (Phase 31.6).
"""

from __future__ import annotations

import re

_BOX_PROPS = frozenset({"padding", "margin"})
_BORDER_STYLES = frozenset(
    {
        "none",
        "hidden",
        "dotted",
        "dashed",
        "solid",
        "double",
        "groove",
        "ridge",
        "inset",
        "outset",
    }
)


def expand_shorthands(css_text: str) -> str:
    """Expand shorthand declarations in a semicolon-delimited CSS string.

    Returns the CSS text with shorthands replaced by their longhand equivalents.
    """
    parts: list[str] = []
    for segment in css_text.split(";"):
        segment = segment.strip()
        if not segment or ":" not in segment:
            if segment:
                parts.append(segment)
            continue
        prop, val = segment.split(":", 1)
        prop = prop.strip().lower()
        val = val.strip()

        expanded = _try_expand(prop, val)
        if expanded:
            parts.extend(f"{p}: {v}" for p, v in expanded)
        else:
            parts.append(f"{prop}: {val}")

    return "; ".join(parts)


def _try_expand(prop: str, val: str) -> list[tuple[str, str]] | None:
    """Try to expand a single property. Returns None if not a shorthand."""
    if prop in _BOX_PROPS:
        return _expand_box(prop, val)
    if prop == "border":
        return _expand_border(val)
    if prop == "background":
        return _expand_background(val)
    if prop == "font":
        return _expand_font(val)
    return None


def _expand_box(prop: str, val: str) -> list[tuple[str, str]]:
    """Expand padding/margin shorthand."""
    tokens = val.split()
    if len(tokens) == 1:
        top = right = bottom = left = tokens[0]
    elif len(tokens) == 2:
        top = bottom = tokens[0]
        right = left = tokens[1]
    elif len(tokens) == 3:
        top, right, bottom = tokens[0], tokens[1], tokens[2]
        left = tokens[1]
    else:
        top, right, bottom, left = tokens[0], tokens[1], tokens[2], tokens[3]

    return [
        (f"{prop}-top", top),
        (f"{prop}-right", right),
        (f"{prop}-bottom", bottom),
        (f"{prop}-left", left),
    ]


def _expand_border(val: str) -> list[tuple[str, str]]:
    """Expand border shorthand."""
    tokens = val.split()
    result: list[tuple[str, str]] = []
    for token in tokens:
        if re.match(r"^\d", token):
            result.append(("border-width", token))
        elif token.lower() in _BORDER_STYLES:
            result.append(("border-style", token))
        else:
            result.append(("border-color", token))
    return result if result else [("border", val)]


def _expand_background(val: str) -> list[tuple[str, str]] | None:
    """Expand background shorthand."""
    result: list[tuple[str, str]] = []

    url_match = re.search(r"url\([^)]*\)", val, re.IGNORECASE)
    if url_match:
        result.append(("background-image", url_match.group()))

    color_match = re.search(r"#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)", val, re.IGNORECASE)
    if color_match:
        result.append(("background-color", color_match.group()))

    repeat_match = re.search(r"\b(repeat|no-repeat|repeat-x|repeat-y|space|round)\b", val)
    if repeat_match:
        result.append(("background-repeat", repeat_match.group(1)))

    pos_match = re.search(r"\b(top|bottom|left|right|center)\b", val)
    if pos_match:
        result.append(("background-position", pos_match.group(1)))

    return result if result else None


_FONT_RE = re.compile(
    r"^(italic|oblique)?\s*"
    r"(small-caps)?\s*"
    r"(bold|bolder|lighter|normal|\d{3})?\s*"
    r"(\d+[\w%]+)\s*"
    r"(?:/\s*([\d.]+[\w%]*))?"
    r"[\s,]+(.+)$",
    re.IGNORECASE,
)


def _expand_font(val: str) -> list[tuple[str, str]] | None:
    """Expand font shorthand."""
    m = _FONT_RE.match(val.strip())
    if not m:
        return None
    result: list[tuple[str, str]] = []
    if m.group(1):
        result.append(("font-style", m.group(1)))
    if m.group(2):
        result.append(("font-variant", m.group(2)))
    if m.group(3):
        result.append(("font-weight", m.group(3)))
    result.append(("font-size", m.group(4)))
    if m.group(5):
        result.append(("line-height", m.group(5)))
    result.append(("font-family", m.group(6).strip()))
    return result
