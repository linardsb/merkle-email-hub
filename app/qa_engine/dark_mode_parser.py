"""Dark mode semantic parser and validator.

Provides validate_dark_mode() for use by:
- QA dark_mode check (via rule engine custom functions)
- Dark Mode agent (direct import for post-generation validation)

Parses meta tags via lxml DOM, CSS patterns via regex on raw HTML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml.html import HtmlElement

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetaTagInfo:
    """Parsed state of dark mode meta tags."""

    has_color_scheme: bool = False
    has_supported_color_schemes: bool = False
    has_css_color_scheme: bool = False
    color_scheme_in_head: bool = True  # True when not present (no misplacement)
    content_value: str = ""


@dataclass(frozen=True)
class CSSDeclaration:
    """A single CSS declaration inside a dark mode media query."""

    property: str
    value: str
    has_important: bool = False


@dataclass(frozen=True)
class MediaQueryBlock:
    """A parsed @media (prefers-color-scheme: dark) block."""

    content: str
    declarations: tuple[CSSDeclaration, ...] = ()
    has_color_props: bool = False
    has_important: bool = False
    is_empty: bool = True


@dataclass(frozen=True)
class OutlookSelector:
    """A parsed [data-ogsc] or [data-ogsb] CSS rule block."""

    selector_type: str  # "ogsc" | "ogsb"
    rules: str = ""
    has_declarations: bool = False


@dataclass(frozen=True)
class ColorPair:
    """A light→dark color mapping extracted from CSS."""

    selector: str
    css_property: str
    light_value: str
    dark_value: str
    contrast_ratio: float = 0.0


@dataclass
class DarkModeValidationResult:
    """Aggregate result of dark mode validation."""

    issues: list[str] = field(default_factory=lambda: list[str]())
    meta_tags: MetaTagInfo = field(default_factory=MetaTagInfo)
    media_queries: list[MediaQueryBlock] = field(default_factory=lambda: list[MediaQueryBlock]())
    outlook_selectors: list[OutlookSelector] = field(
        default_factory=lambda: list[OutlookSelector]()
    )
    color_pairs: list[ColorPair] = field(default_factory=lambda: list[ColorPair]())
    has_image_swap: bool = False
    has_1x1_trick: bool = False


# ---------------------------------------------------------------------------
# Regex patterns (compiled once)
# ---------------------------------------------------------------------------

# @media (prefers-color-scheme: dark) { ... } — capture the block content
_MEDIA_DARK_RE = re.compile(
    r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{",
    re.IGNORECASE,
)

# CSS declaration: property: value [!important];
_CSS_DECL_RE = re.compile(
    r"([\w-]+)\s*:\s*([^;{}]+?)\s*(!\s*important)?\s*[;}\n]",
    re.IGNORECASE,
)

# Color-related CSS properties
_COLOR_PROPERTIES = frozenset(
    {
        "color",
        "background-color",
        "background",
        "border-color",
        "border",
        "border-top-color",
        "border-right-color",
        "border-bottom-color",
        "border-left-color",
    }
)

# [data-ogsc] and [data-ogsb] selector blocks
_OGSC_BLOCK_RE = re.compile(
    r"\[data-ogsc\]\s*[^{]*\{([^}]*)\}",
    re.IGNORECASE,
)
_OGSB_BLOCK_RE = re.compile(
    r"\[data-ogsb\]\s*[^{]*\{([^}]*)\}",
    re.IGNORECASE,
)

# CSS color-scheme property in style blocks (not inside @media queries)
# Matches standalone property like `:root { color-scheme: light dark; }`
# but NOT `@media (prefers-color-scheme: dark)` which is a media query
_CSS_COLOR_SCHEME_RE = re.compile(
    r"(?<!\()color-scheme\s*:\s*[^;)]*dark[^;)]*;",
    re.IGNORECASE,
)

# Hex color values
_HEX_COLOR_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")

# Named colors (common ones)
_NAMED_COLORS: dict[str, str] = {
    "white": "#ffffff",
    "black": "#000000",
    "transparent": "#000000",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "gray": "#808080",
    "grey": "#808080",
    "navy": "#000080",
    "silver": "#c0c0c0",
    "maroon": "#800000",
    "purple": "#800080",
    "teal": "#008080",
    "olive": "#808000",
    "aqua": "#00ffff",
    "fuchsia": "#ff00ff",
    "lime": "#00ff00",
    "orange": "#ffa500",
}

# rgb(r, g, b) pattern
_RGB_RE = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", re.IGNORECASE)

# Image swap patterns
_PICTURE_SOURCE_DARK_RE = re.compile(
    r'<source\b[^>]*media=["\'][^"\']*prefers-color-scheme\s*:\s*dark[^"\']*["\']',
    re.IGNORECASE,
)
_DARK_IMG_CLASS_RE = re.compile(
    r"\.(dark[-_]?img|dark[-_]?image|dark[-_]?logo)\b",
    re.IGNORECASE,
)
_1X1_BACKGROUND_RE = re.compile(
    r"background-image\s*:\s*url\s*\(",
    re.IGNORECASE,
)

# Inline style class-to-selector matching
_CLASS_ATTR_RE = re.compile(r'class\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

# CSS rule: .selector { declarations }
_CSS_RULE_RE = re.compile(
    r"\.([a-zA-Z][\w-]*)\s*\{([^}]*)\}",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------


def _parse_css_color(value: str) -> str | None:
    """Extract a normalised hex color from a CSS value.

    Handles #hex, rgb(), and common named colors.
    Returns None if no color can be extracted.
    """
    value = value.strip().lower()

    # Check named colors first
    if value in _NAMED_COLORS:
        return _NAMED_COLORS[value]

    # Check hex
    hex_match = _HEX_COLOR_RE.search(value)
    if hex_match:
        hex_val = hex_match.group(1)
        if len(hex_val) == 3:
            hex_val = "".join(c * 2 for c in hex_val)
        elif len(hex_val) == 4:
            hex_val = "".join(c * 2 for c in hex_val[:3])
        elif len(hex_val) > 6:
            hex_val = hex_val[:6]
        return f"#{hex_val}"

    # Check rgb()
    rgb_match = _RGB_RE.search(value)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return f"#{r:02x}{g:02x}{b:02x}"

    return None


def _hex_to_luminance(hex_color: str) -> float:
    """Convert hex color to WCAG 2.1 relative luminance."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)

    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    # sRGB linearisation
    def linearise(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearise(r) + 0.7152 * linearise(g) + 0.0722 * linearise(b)


def _contrast_ratio(l1: float, l2: float) -> float:
    """Compute WCAG contrast ratio between two luminance values."""
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Sub-validators
# ---------------------------------------------------------------------------


def _extract_media_query_block(raw_html: str, start: int) -> str:
    """Extract the CSS content of a { ... } block starting at `start`."""
    depth = 1
    i = start
    while i < len(raw_html) and depth > 0:
        if raw_html[i] == "{":
            depth += 1
        elif raw_html[i] == "}":
            depth -= 1
        i += 1
    return raw_html[start : i - 1] if depth == 0 else raw_html[start:i]


def _parse_meta_tags(doc: HtmlElement, raw_html: str) -> MetaTagInfo:
    """Parse dark mode meta tag declarations from the DOM."""
    has_color_scheme = False
    has_supported = False
    has_css_color_scheme = False
    color_scheme_in_head = True  # Assume correct until proven otherwise
    content_value = ""

    # Check for <meta name="color-scheme"> via DOM
    for meta in doc.iter("meta"):
        name = (meta.get("name") or "").lower()
        content = meta.get("content") or ""

        if name == "color-scheme":
            has_color_scheme = True
            content_value = content

            # Check placement — is this meta in <head> or <body>?
            parent = meta.getparent()
            while parent is not None:
                tag = parent.tag if isinstance(parent.tag, str) else ""
                if tag.lower() == "body":
                    color_scheme_in_head = False
                    break
                if tag.lower() == "head":
                    break
                parent = parent.getparent()

        elif name == "supported-color-schemes":
            has_supported = True

    # Check for CSS color-scheme property
    has_css_color_scheme = bool(_CSS_COLOR_SCHEME_RE.search(raw_html))

    return MetaTagInfo(
        has_color_scheme=has_color_scheme,
        has_supported_color_schemes=has_supported,
        has_css_color_scheme=has_css_color_scheme,
        color_scheme_in_head=color_scheme_in_head,
        content_value=content_value,
    )


def _parse_media_queries(raw_html: str) -> list[MediaQueryBlock]:
    """Extract and parse @media (prefers-color-scheme: dark) blocks."""
    blocks: list[MediaQueryBlock] = []

    for m in _MEDIA_DARK_RE.finditer(raw_html):
        block_start = m.end()
        content = _extract_media_query_block(raw_html, block_start)

        # Parse declarations within the block
        declarations: list[CSSDeclaration] = []
        has_color = False
        has_important = True  # Assume true, set false if any color decl missing it

        for decl_match in _CSS_DECL_RE.finditer(content):
            prop = decl_match.group(1).lower().strip()
            val = decl_match.group(2).strip()
            imp = bool(decl_match.group(3))

            declarations.append(
                CSSDeclaration(
                    property=prop,
                    value=val,
                    has_important=imp,
                )
            )

            if prop in _COLOR_PROPERTIES:
                has_color = True
                if not imp:
                    has_important = False

        # If no color declarations at all, has_important is vacuously true — mark as true
        if not has_color:
            has_important = True

        blocks.append(
            MediaQueryBlock(
                content=content.strip(),
                declarations=tuple(declarations),
                has_color_props=has_color,
                has_important=has_important,
                is_empty=len(declarations) == 0,
            )
        )

    return blocks


def _parse_outlook_selectors(raw_html: str) -> list[OutlookSelector]:
    """Extract [data-ogsc] and [data-ogsb] CSS rule blocks."""
    selectors: list[OutlookSelector] = []

    for m in _OGSC_BLOCK_RE.finditer(raw_html):
        content = m.group(1).strip()
        selectors.append(
            OutlookSelector(
                selector_type="ogsc",
                rules=content,
                has_declarations=bool(content and _CSS_DECL_RE.search(content)),
            )
        )

    for m in _OGSB_BLOCK_RE.finditer(raw_html):
        content = m.group(1).strip()
        selectors.append(
            OutlookSelector(
                selector_type="ogsb",
                rules=content,
                has_declarations=bool(content and _CSS_DECL_RE.search(content)),
            )
        )

    return selectors


def _extract_color_pairs(
    raw_html: str,
    media_queries: list[MediaQueryBlock],
) -> list[ColorPair]:
    """Extract light→dark color mappings by matching class selectors."""
    pairs: list[ColorPair] = []

    # Build a map of dark mode colors: class.property -> dark_value
    dark_colors: dict[str, tuple[str, str]] = {}  # "class.property" -> (selector, value)
    for mq in media_queries:
        # Parse CSS rules within the media query
        for rule_match in _CSS_RULE_RE.finditer(mq.content):
            selector = rule_match.group(1)
            decl_block = rule_match.group(2)
            for decl_match in _CSS_DECL_RE.finditer(decl_block):
                prop = decl_match.group(1).lower().strip()
                val = decl_match.group(2).strip()
                if prop in _COLOR_PROPERTIES:
                    key = f"{selector}.{prop}"
                    dark_colors[key] = (f".{selector}", val)

    # Find inline styles or class-based light mode colors in the HTML
    # Match dark colors to light colors by class name
    for class_match in _CLASS_ATTR_RE.finditer(raw_html):
        classes = class_match.group(1).split()
        # Get the element's inline style
        # Look backward for style attribute on same element
        tag_start = raw_html.rfind("<", 0, class_match.start())
        tag_end = raw_html.find(">", class_match.end())
        if tag_start == -1 or tag_end == -1:
            continue
        tag_html = raw_html[tag_start : tag_end + 1]

        # Extract inline style colors
        style_match = re.search(r'style\s*=\s*["\']([^"\']*)["\']', tag_html, re.IGNORECASE)
        if not style_match:
            continue

        style_content = style_match.group(1)
        inline_colors: dict[str, str] = {}
        for decl_match in _CSS_DECL_RE.finditer(style_content + ";"):
            prop = decl_match.group(1).lower().strip()
            val = decl_match.group(2).strip()
            if prop in _COLOR_PROPERTIES:
                inline_colors[prop] = val

        # Match with dark mode counterparts
        for cls in classes:
            for prop, light_val in inline_colors.items():
                key = f"{cls}.{prop}"
                if key in dark_colors:
                    dark_selector, dark_val = dark_colors[key]
                    light_hex = _parse_css_color(light_val)
                    dark_hex = _parse_css_color(dark_val)
                    ratio = 0.0
                    if light_hex and dark_hex:
                        l1 = _hex_to_luminance(light_hex)
                        l2 = _hex_to_luminance(dark_hex)
                        ratio = round(_contrast_ratio(l1, l2), 2)

                    pairs.append(
                        ColorPair(
                            selector=dark_selector,
                            css_property=prop,
                            light_value=light_val,
                            dark_value=dark_val,
                            contrast_ratio=ratio,
                        )
                    )

    return pairs


def _detect_image_patterns(raw_html: str) -> tuple[bool, bool]:
    """Detect dark mode image handling patterns.

    Returns:
        (has_image_swap, has_1x1_trick)
    """
    has_image_swap = bool(
        _PICTURE_SOURCE_DARK_RE.search(raw_html) or _DARK_IMG_CLASS_RE.search(raw_html)
    )
    has_1x1_trick = (
        bool(_1X1_BACKGROUND_RE.search(raw_html)) and "background-color" in raw_html.lower()
    )

    return has_image_swap, has_1x1_trick


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_dark_mode(html: str) -> DarkModeValidationResult:
    """Validate dark mode implementation in email HTML.

    This is the public API used by:
    - QA dark_mode check (via custom check functions)
    - Dark Mode agent (direct import for post-generation validation)
    """
    result = DarkModeValidationResult()

    if not html or not html.strip():
        return result

    # Parse DOM for meta tags
    from lxml import html as lxml_html

    try:
        doc = lxml_html.document_fromstring(html)
    except Exception:
        logger.warning("dark_mode_parser.parse_failed", html_length=len(html))
        return result

    # 1. Meta tags
    result.meta_tags = _parse_meta_tags(doc, html)

    # 2. Media queries
    result.media_queries = _parse_media_queries(html)

    # 3. Outlook selectors
    result.outlook_selectors = _parse_outlook_selectors(html)

    # 4. Color pairs
    result.color_pairs = _extract_color_pairs(html, result.media_queries)

    # 5. Image patterns
    result.has_image_swap, result.has_1x1_trick = _detect_image_patterns(html)

    logger.debug(
        "dark_mode_parser.validation_complete",
        has_color_scheme=result.meta_tags.has_color_scheme,
        media_queries=len(result.media_queries),
        outlook_selectors=len(result.outlook_selectors),
        color_pairs=len(result.color_pairs),
        has_image_swap=result.has_image_swap,
    )

    return result


# ---------------------------------------------------------------------------
# Caching layer for QA check integration
# ---------------------------------------------------------------------------

_dm_cache: dict[str, DarkModeValidationResult] = {}


def get_cached_dm_result(raw_html: str) -> DarkModeValidationResult:
    """Get cached dark mode validation result, computing if not cached.

    Used by custom check functions to avoid re-parsing the same HTML
    across multiple rule evaluations within a single check run.
    Cache is cleared at the start of each DarkModeCheck.run() call,
    so it holds at most one entry per run.
    """
    if raw_html not in _dm_cache:
        _dm_cache[raw_html] = validate_dark_mode(raw_html)
    return _dm_cache[raw_html]


def clear_dm_cache() -> None:
    """Clear the dark mode validation cache. Called at the start of each check run."""
    _dm_cache.clear()
