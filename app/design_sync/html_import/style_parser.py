"""Low-level CSS parsing utilities for HTML email import."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Named CSS colors (common 17) ──────────────────────────────────


_NAMED_COLORS: dict[str, str] = {
    "white": "#ffffff",
    "black": "#000000",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "orange": "#ffa500",
    "purple": "#800080",
    "gray": "#808080",
    "grey": "#808080",
    "silver": "#c0c0c0",
    "maroon": "#800000",
    "navy": "#000080",
    "teal": "#008080",
    "aqua": "#00ffff",
    "fuchsia": "#ff00ff",
    "lime": "#00ff00",
}

_HEX3_RE = re.compile(r"^#([0-9a-fA-F]{3})$")
_HEX6_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
_RGB_RE = re.compile(
    r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)",
    re.IGNORECASE,
)
_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
_FONT_SIZE_RE = re.compile(r"^([\d.]+)\s*(px|pt|em|rem)$", re.IGNORECASE)


# ── Dataclass ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class ParsedStyle:
    """Parsed inline CSS properties."""

    properties: dict[str, str] = field(default_factory=dict[str, str])


@dataclass(frozen=True)
class CssRule:
    """A single CSS rule: selector → properties."""

    selector: str
    properties: dict[str, str]
    is_dark_mode: bool = False


# ── Parsing functions ──────────────────────────────────────────────


def parse_inline_style(style_attr: str) -> ParsedStyle:
    """Parse a CSS ``style`` attribute string into a property dict.

    Strips ``!important``, normalises property names to lowercase,
    and preserves quoted font-family values.
    """
    if not style_attr or not style_attr.strip():
        return ParsedStyle()

    props: dict[str, str] = {}
    # Split on semicolons but respect quotes
    for declaration in style_attr.split(";"):
        declaration = declaration.strip()
        if not declaration or ":" not in declaration:
            continue
        prop, _, value = declaration.partition(":")
        prop = prop.strip().lower()
        value = value.strip().rstrip(";")
        # Strip !important
        value = re.sub(r"\s*!important\s*$", "", value, flags=re.IGNORECASE)
        if prop and value:
            props[prop] = value

    return ParsedStyle(properties=props)


def parse_style_blocks(html: str) -> list[str]:
    """Extract all ``<style>`` block contents from an HTML string.

    Returns the inner CSS text of each block, preserving ``@media`` blocks.
    """
    return _STYLE_BLOCK_RE.findall(html)


def parse_css_rules(css_text: str) -> list[CssRule]:
    """Parse CSS text into ``CssRule`` objects.

    Detects ``@media (prefers-color-scheme: dark)`` blocks and marks
    rules inside them with ``is_dark_mode=True``.
    """
    rules: list[CssRule] = []
    _parse_rules_from_text(css_text, is_dark_mode=False, out=rules)
    return rules


def _parse_rules_from_text(css_text: str, *, is_dark_mode: bool, out: list[CssRule]) -> None:
    """Recursively parse CSS rules, handling @media blocks."""
    # Find @media (prefers-color-scheme: dark) blocks
    dark_re = re.compile(
        r"@media\s*\([^)]*prefers-color-scheme\s*:\s*dark[^)]*\)\s*\{",
        re.IGNORECASE,
    )
    pos = 0
    while pos < len(css_text):
        m = dark_re.search(css_text, pos)
        if m is None:
            # Parse remaining as regular rules
            _extract_simple_rules(css_text[pos:], is_dark_mode=is_dark_mode, out=out)
            break

        # Parse rules before the @media block
        _extract_simple_rules(css_text[pos : m.start()], is_dark_mode=is_dark_mode, out=out)

        # Find matching closing brace
        brace_start = m.end()
        depth = 1
        i = brace_start
        while i < len(css_text) and depth > 0:
            if css_text[i] == "{":
                depth += 1
            elif css_text[i] == "}":
                depth -= 1
            i += 1

        inner = css_text[brace_start : i - 1] if depth == 0 else css_text[brace_start:]
        _parse_rules_from_text(inner, is_dark_mode=True, out=out)
        pos = i

    return


def _extract_simple_rules(css_text: str, *, is_dark_mode: bool, out: list[CssRule]) -> None:
    """Extract non-nested CSS rules from text."""
    # Simple rule: selector { declarations }
    rule_re = re.compile(r"([^{}]+?)\{([^{}]*)\}")
    for m in rule_re.finditer(css_text):
        selector = m.group(1).strip()
        declarations = m.group(2).strip()
        if not selector or not declarations:
            continue
        # Skip @-rules other than @media (already handled)
        if selector.startswith("@"):
            continue
        props = parse_inline_style(declarations).properties
        if props:
            out.append(CssRule(selector=selector, properties=props, is_dark_mode=is_dark_mode))


def extract_font_size_px(value: str) -> float | None:
    """Normalise a CSS size value to pixels.

    Handles ``px``, ``pt`` (x1.333), ``em``/``rem`` (x16), and bare
    unitless numbers (returned as-is — useful for line-height multipliers
    which the caller converts relative to font-size).
    Returns ``None`` if the value cannot be parsed.
    """
    if not value:
        return None

    value = value.strip().lower()
    m = _FONT_SIZE_RE.match(value)
    if m:
        num = float(m.group(1))
        unit = m.group(2).lower()

        if unit == "px":
            return num
        if unit == "pt":
            return round(num * 1.333, 1)
        if unit in ("em", "rem"):
            return round(num * 16.0, 1)
        return None

    # Bare unitless number (e.g. line-height: 1.5)
    try:
        return float(value)
    except ValueError:
        return None


def normalize_hex_color(value: str) -> str | None:
    """Normalise a CSS colour value to 6-digit lowercase hex.

    Handles ``#RGB``, ``#RRGGBB``, ``rgb(r,g,b)``, and named colours.
    Returns ``None`` if the value cannot be parsed.
    """
    if not value:
        return None

    value = value.strip().lower()

    # Transparent / fully-transparent rgba → no colour
    if value in ("transparent", "rgba(0, 0, 0, 0)", "rgba(0,0,0,0)"):
        return None

    # Named colour
    if value in _NAMED_COLORS:
        return _NAMED_COLORS[value]

    # #RRGGBB
    m = _HEX6_RE.match(value)
    if m:
        return f"#{m.group(1).lower()}"

    # #RGB → #RRGGBB
    m = _HEX3_RE.match(value)
    if m:
        short = m.group(1)
        r, g, b = short[0], short[1], short[2]
        return f"#{r}{r}{g}{g}{b}{b}".lower()

    # rgb(r, g, b)
    m = _RGB_RE.match(value)
    if m:
        r_val = min(255, max(0, int(m.group(1))))
        g_val = min(255, max(0, int(m.group(2))))
        b_val = min(255, max(0, int(m.group(3))))
        return f"#{r_val:02x}{g_val:02x}{b_val:02x}"

    return None


def parse_padding_shorthand(value: str) -> tuple[float, float, float, float] | None:
    """Parse CSS padding shorthand into (top, right, bottom, left).

    Handles 1-value, 2-value, 3-value, and 4-value notation.
    Returns ``None`` if the value cannot be parsed.
    """
    if not value:
        return None

    parts = value.strip().split()
    values: list[float] = []
    for part in parts:
        px = extract_font_size_px(part)  # reuse px/pt/em parser
        if px is None:
            # Try bare number (assume px)
            try:
                px = float(part.replace("px", ""))
            except ValueError:
                return None
        values.append(px)

    if len(values) == 1:
        return (values[0], values[0], values[0], values[0])
    if len(values) == 2:
        return (values[0], values[1], values[0], values[1])
    if len(values) == 3:
        return (values[0], values[1], values[2], values[1])
    if len(values) == 4:
        return (values[0], values[1], values[2], values[3])
    return None
