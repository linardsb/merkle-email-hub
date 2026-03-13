"""Brand compliance analyzer — CSS color/font extraction and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from lxml.html import HtmlElement

# ── Color extraction ──

# Match hex (#fff, #ffffff), rgb(), rgba(), named colors
_HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}\b")
_RGB_COLOR = re.compile(r"rgba?\([^)]+\)")
_NAMED_COLORS: frozenset[str] = frozenset(
    {
        "red",
        "blue",
        "green",
        "black",
        "white",
        "gray",
        "grey",
        "orange",
        "yellow",
        "purple",
        "pink",
        "brown",
        "navy",
        "teal",
        "maroon",
        "olive",
        "aqua",
        "fuchsia",
        "silver",
        "lime",
    }
)
_CSS_COLOR_PROP = re.compile(
    r"(?:color|background-color|background|border-color|border)\s*:\s*([^;}{]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BrandAnalysis:
    """Cached result of brand analysis on an HTML document."""

    colors_found: frozenset[str]  # Normalized lowercase hex/rgb/named
    fonts_found: frozenset[str]  # Normalized lowercase font family names
    has_footer: bool
    has_logo: bool
    has_unsubscribe: bool
    raw_text: str  # Full text content for pattern matching


def _normalize_color(color: str) -> str:
    """Normalize color to lowercase. Expand 3-char hex to 6-char."""
    c = color.strip().lower()
    if re.match(r"^#[0-9a-f]{3}$", c):
        return f"#{c[1] * 2}{c[2] * 2}{c[3] * 2}"
    return c


def extract_colors(doc: HtmlElement, raw_html: str) -> frozenset[str]:  # noqa: ARG001
    """Extract all CSS colors from style blocks and inline styles."""
    colors: set[str] = set()

    # Collect all CSS text
    css_texts: list[str] = []
    for style in doc.iter("style"):
        if style.text:
            css_texts.append(style.text)
    for el in doc.iter():
        if isinstance(el.tag, str):
            inline = el.get("style")
            if inline:
                css_texts.append(inline)

    combined = " ".join(css_texts)

    # Extract from color properties
    for match in _CSS_COLOR_PROP.finditer(combined):
        value = match.group(1).strip().lower()
        # Hex colors
        for hex_match in _HEX_COLOR.finditer(value):
            colors.add(_normalize_color(hex_match.group()))
        # RGB/RGBA
        for rgb_match in _RGB_COLOR.finditer(value):
            colors.add(rgb_match.group().lower().replace(" ", ""))
        # Named colors
        for word in value.split():
            clean = word.strip(" ,;")
            clean = clean.replace("!important", "")
            if clean in _NAMED_COLORS:
                colors.add(clean)

    return frozenset(colors)


_FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}{]+)", re.IGNORECASE)


def extract_fonts(doc: HtmlElement, raw_html: str) -> frozenset[str]:  # noqa: ARG001
    """Extract all font-family declarations."""
    fonts: set[str] = set()

    css_texts: list[str] = []
    for style in doc.iter("style"):
        if style.text:
            css_texts.append(style.text)
    for el in doc.iter():
        if isinstance(el.tag, str):
            inline = el.get("style")
            if inline:
                css_texts.append(inline)

    combined = " ".join(css_texts)

    for match in _FONT_FAMILY.finditer(combined):
        families = match.group(1)
        for font in families.split(","):
            clean = font.strip().strip("'\"").strip().lower()
            if clean and clean not in ("inherit", "initial", "unset"):
                fonts.add(clean)

    return frozenset(fonts)


def detect_required_elements(doc: HtmlElement, raw_html: str) -> tuple[bool, bool, bool]:
    """Detect footer, logo, and unsubscribe link presence.

    Returns: (has_footer, has_logo, has_unsubscribe)
    """
    raw_lower = raw_html.lower()

    # Footer: element with class/id containing "footer", or semantic <footer>
    has_footer = False
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag == "footer":
            has_footer = True
            break
        cls = (el.get("class") or "").lower()
        el_id = (el.get("id") or "").lower()
        if "footer" in cls or "footer" in el_id:
            has_footer = True
            break

    # Logo: img with class/id/alt containing "logo"
    has_logo = False
    for img in doc.iter("img"):
        alt = (img.get("alt") or "").lower()
        cls = (img.get("class") or "").lower()
        el_id = (img.get("id") or "").lower()
        src = (img.get("src") or "").lower()
        if "logo" in alt or "logo" in cls or "logo" in el_id or "logo" in src:
            has_logo = True
            break

    # Unsubscribe: link with text or href containing "unsubscribe"
    has_unsubscribe = False
    for a in doc.iter("a"):
        href = (a.get("href") or "").lower()
        text = (a.text_content() or "").lower()
        if "unsubscribe" in href or "unsubscribe" in text:
            has_unsubscribe = True
            break
    # Also check List-Unsubscribe in raw HTML (header-based)
    if not has_unsubscribe and "unsubscribe" in raw_lower:
        has_unsubscribe = True

    return has_footer, has_logo, has_unsubscribe


# ── Cached analysis ──

_analysis_cache: dict[int, BrandAnalysis] = {}


def analyze_brand(doc: HtmlElement, raw_html: str) -> BrandAnalysis:
    """Get cached brand analysis for an HTML document."""
    cache_key = id(doc)
    if cache_key in _analysis_cache:
        return _analysis_cache[cache_key]

    colors = extract_colors(doc, raw_html)
    fonts = extract_fonts(doc, raw_html)
    has_footer, has_logo, has_unsub = detect_required_elements(doc, raw_html)
    text = doc.text_content() or ""

    analysis = BrandAnalysis(
        colors_found=colors,
        fonts_found=fonts,
        has_footer=has_footer,
        has_logo=has_logo,
        has_unsubscribe=has_unsub,
        raw_text=text,
    )
    _analysis_cache[cache_key] = analysis
    return analysis


def clear_brand_cache() -> None:
    """Clear the analysis cache. Called at start of each check run."""
    _analysis_cache.clear()
