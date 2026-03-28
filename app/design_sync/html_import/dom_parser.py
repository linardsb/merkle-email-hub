"""DOM-based section extraction from arbitrary email HTML."""

from __future__ import annotations

import hashlib
import html as html_mod
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.design_sync.email_design_document import (
    DocumentButton,
    DocumentColumn,
    DocumentImage,
    DocumentPadding,
    DocumentSection,
    DocumentText,
)
from app.design_sync.html_import.style_parser import (
    extract_font_size_px,
    normalize_hex_color,
    parse_inline_style,
    parse_padding_shorthand,
    parse_style_blocks,
)

# ── Result dataclass ───────────────────────────────────────────────


@dataclass(frozen=True)
class ParsedEmail:
    """Result of DOM parsing."""

    sections: list[DocumentSection] = field(default_factory=list[DocumentSection])
    container_width: int = 600
    has_mso_conditionals: bool = False
    has_dark_mode: bool = False
    style_blocks: list[str] = field(default_factory=list[str])
    meta_charset: str | None = None
    preheader_text: str | None = None


# ── Heading detection ──────────────────────────────────────────────

_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_TEXT_TAGS = frozenset(
    {
        "td",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "span",
        "a",
        "b",
        "strong",
        "em",
        "i",
        "u",
        "li",
        "blockquote",
    }
)
_INLINE_TAGS = frozenset({"b", "strong", "em", "i", "u", "s", "sub", "sup", "span", "a"})
_HIDDEN_RE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)
_MSO_COMMENT_RE = re.compile(r"<!--\[if\s+mso", re.IGNORECASE)
_SOCIAL_URL_PARTS = frozenset({"facebook", "twitter", "linkedin", "instagram", "youtube", "x.com"})


# ── Main entry ─────────────────────────────────────────────────────


def parse_email_dom(raw_html: str) -> ParsedEmail:
    """Parse an email HTML string into structured sections.

    Pipeline:
    1. Parse with lxml
    2. Extract ``<style>`` blocks
    3. Detect container width
    4. Find content table (skip MSO wrappers)
    5. Walk top-level ``<tr>`` rows → candidate sections
    6. For each section: extract texts, images, buttons, columns, styling
    """
    if not raw_html or not raw_html.strip():
        return ParsedEmail()

    style_blocks = parse_style_blocks(raw_html)
    has_mso = bool(_MSO_COMMENT_RE.search(raw_html))
    has_dark = any("prefers-color-scheme" in sb for sb in style_blocks)

    root: HtmlElement = lxml_html.fromstring(raw_html)

    charset = _detect_charset(root)
    preheader = _detect_preheader(root)

    container_width, section_elements = _find_sections(root)

    sections: list[DocumentSection] = []
    y_offset = 0.0
    for idx, elem in enumerate(section_elements):
        section = _build_section(elem, idx, y_offset, container_width)
        sections.append(section)
        y_offset += section.height if section.height is not None else 0.0

    return ParsedEmail(
        sections=sections,
        container_width=container_width,
        has_mso_conditionals=has_mso,
        has_dark_mode=has_dark,
        style_blocks=style_blocks,
        meta_charset=charset,
        preheader_text=preheader,
    )


# ── Content table / section detection ──────────────────────────────


def _find_sections(root: HtmlElement) -> tuple[int, list[HtmlElement]]:
    """Find sections in the email HTML.

    Strategy (in order):
    1. Import annotator annotations (``data-section-id``)
    2. Single content table with multiple ``<tr>`` rows
    3. Multiple sibling tables as individual sections (common in golden templates)
    4. All top-level tables as sections (fallback)

    Returns (container_width, list_of_section_elements).
    """
    # Strategy 1: Import annotator annotations
    annotated: list[HtmlElement] = root.xpath("//*[@data-section-id]")
    if annotated:
        width = _detect_container_width_from_root(root)
        return (width, annotated)

    # Strategy 2: Find a fixed-width content table with <tr> rows
    content_table = _find_content_table(root)
    if content_table is not None:
        rows = _extract_tr_rows(content_table)
        if len(rows) >= 2:
            width = _detect_container_width(content_table)
            return (width, rows)

    # Strategy 3: Multiple sibling tables (each is a section)
    wrapper = _find_content_wrapper(root)
    if wrapper is not None:
        tables: list[HtmlElement] = []
        for child in wrapper:
            if isinstance(child.tag, str) and child.tag == "table":
                tables.append(child)
        if len(tables) >= 2:
            width = _detect_container_width_from_root(root)
            return (width, tables)

    # Strategy 4: All tables with role="presentation" as sections
    all_tables = [t for t in root.iter("table") if t.get("role") == "presentation"]
    if all_tables:
        width = _detect_container_width_from_root(root)
        return (width, all_tables)

    # Last resort: any tables
    any_tables = list(root.iter("table"))
    if any_tables:
        width = _detect_container_width_from_root(root)
        return (width, any_tables)

    return (600, [])


def _find_content_wrapper(root: HtmlElement) -> HtmlElement | None:
    """Find the div/td that wraps section tables (e.g. max-width container)."""
    # Look for a div with max-width style (common in responsive email layouts)
    for div in root.iter("div"):
        style = parse_inline_style(div.get("style", ""))
        max_w = style.properties.get("max-width", "")
        if max_w and any(w in max_w for w in ("600", "640", "580", "700")):
            return div

    # Look for body or first major container
    body = root.find(".//body")
    if body is not None:
        # Check first child div
        for child in body:
            if isinstance(child.tag, str) and child.tag == "div":
                return child
    return None


def _detect_container_width_from_root(root: HtmlElement) -> int:
    """Detect container width from any element in the tree."""
    # Check for max-width on wrapper divs
    for div in root.iter("div"):
        style = parse_inline_style(div.get("style", ""))
        for prop in ("max-width", "width"):
            val = style.properties.get(prop, "")
            if val:
                num = re.search(r"(\d+)", val)
                if num and 320 <= int(num.group(1)) <= 1200:
                    return int(num.group(1))

    # Check tables
    for table in root.iter("table"):
        w = _detect_container_width(table)
        if w != 600:
            return w

    return 600


def _find_content_table(root: HtmlElement) -> HtmlElement | None:
    """Find the primary content table, preferring fixed-width ones."""
    tables = root.iter("table")
    best: HtmlElement | None = None
    best_score = -1

    for table in tables:
        score = 0
        width_attr = table.get("width", "")
        style = parse_inline_style(table.get("style", ""))

        # Width attribute match
        if width_attr in ("600", "640", "580", "700"):
            score += 10
        # max-width or width in style
        for prop in ("max-width", "width"):
            val = style.properties.get(prop, "")
            if val and any(w in val for w in ("600", "640", "580", "700")):
                score += 10

        # role="presentation" (common in email)
        if table.get("role") == "presentation":
            score += 2

        # Prefer tables with more descendant content
        descendant_count = len(list(table.iter()))
        score += min(descendant_count // 10, 5)

        # Prefer tables at higher DOM level (fewer ancestors)
        ancestors = len(list(table.iterancestors()))
        score -= ancestors

        if score > best_score:
            best_score = score
            best = table

    return best


def _detect_container_width(table: HtmlElement) -> int:
    """Detect the container width from a table element."""
    width_attr = table.get("width", "")
    if width_attr.isdigit():
        return int(width_attr)

    style = parse_inline_style(table.get("style", ""))
    for prop in ("width", "max-width"):
        val = style.properties.get(prop, "")
        if val:
            num = re.search(r"(\d+)", val)
            if num:
                return int(num.group(1))
    return 600


def _extract_tr_rows(table: HtmlElement) -> list[HtmlElement]:
    """Get top-level ``<tr>`` elements from a table."""
    rows: list[HtmlElement] = []
    for child in table:
        if isinstance(child.tag, str):
            if child.tag == "tbody":
                for tr in child:
                    if isinstance(tr.tag, str) and tr.tag == "tr":
                        rows.append(tr)
            elif child.tag == "tr":
                rows.append(child)
    return rows


# ── Section building ───────────────────────────────────────────────


def _build_section(
    element: HtmlElement,
    idx: int,
    y_offset: float,
    container_width: int,
) -> DocumentSection:
    """Build a DocumentSection from a row/annotated element."""
    # Use annotator attributes if present
    section_id = element.get("data-section-id", f"section-{idx}")
    section_type = element.get("data-section-type", "unknown")

    texts = _extract_texts(element)
    images = _extract_images(element)
    buttons = _extract_buttons(element)
    col_layout, columns = _detect_columns(element)
    bg_color = _extract_background(element)
    padding = _extract_padding(element)

    # Estimate height from content
    height = _estimate_height(element)

    return DocumentSection(
        id=section_id,
        type=section_type,
        node_name=element.get("data-section-name"),
        y_position=y_offset,
        width=float(container_width),
        height=height,
        column_layout=col_layout,
        column_count=max(1, len(columns)),
        padding=padding,
        background_color=bg_color,
        texts=texts,
        images=images,
        buttons=buttons,
        columns=columns,
    )


# ── Text extraction ────────────────────────────────────────────────


def _extract_texts(element: HtmlElement) -> list[DocumentText]:
    """Recursively extract text content from text-bearing elements."""
    results: list[DocumentText] = []
    _walk_for_texts(element, results)
    return results


def _walk_for_texts(element: HtmlElement, out: list[DocumentText]) -> None:
    """Walk DOM tree collecting text nodes."""
    tag = element.tag if isinstance(element.tag, str) else ""

    # Skip hidden elements
    style_attr = element.get("style", "")
    if style_attr and _HIDDEN_RE.search(style_attr):
        return

    if tag in _TEXT_TAGS:
        text = _get_direct_text(element)
        if text and text.strip():
            style = parse_inline_style(style_attr)
            font_size = extract_font_size_px(style.properties.get("font-size", ""))
            font_weight_str = style.properties.get("font-weight", "")
            font_weight = _parse_font_weight(font_weight_str)
            line_height = extract_font_size_px(style.properties.get("line-height", ""))
            font_family = style.properties.get("font-family", "").strip("'\"") or None
            color = normalize_hex_color(style.properties.get("color", ""))

            is_heading = tag in _HEADING_TAGS or (font_size is not None and font_size > 20.0)

            out.append(
                DocumentText(
                    node_id=_make_node_id(element),
                    content=html_mod.escape(text.strip()),
                    font_size=font_size,
                    is_heading=is_heading,
                    font_family=font_family,
                    font_weight=font_weight,
                    line_height=line_height,
                    color=color,
                )
            )

    for child in element:
        if isinstance(child.tag, str):
            _walk_for_texts(child, out)


def _get_direct_text(element: HtmlElement) -> str:
    """Get the combined text content of an element, recursing into inline tags."""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        tag = child.tag if isinstance(child.tag, str) else ""
        if tag in _INLINE_TAGS:
            # Recurse into inline formatting tags (b, strong, em, etc.)
            parts.append(_get_direct_text(child))
        if child.tail:
            parts.append(child.tail)
    return " ".join(p for p in parts if p.strip())


def _parse_font_weight(value: str) -> int | None:
    """Parse CSS font-weight to integer."""
    if not value:
        return None
    value = value.strip().lower()
    if value == "bold":
        return 700
    if value == "normal":
        return 400
    if value == "lighter":
        return 300
    if value == "bolder":
        return 800
    if value.isdigit():
        return int(value)
    return None


# ── Image extraction ───────────────────────────────────────────────


def _extract_images(element: HtmlElement) -> list[DocumentImage]:
    """Find all ``<img>`` tags and extract metadata."""
    results: list[DocumentImage] = []
    for img in element.iter("img"):
        src = img.get("src", "")
        # Security: only allow http/https URLs
        if src:
            parsed_url = urlparse(src)
            if parsed_url.scheme not in ("http", "https", ""):
                continue

        alt = img.get("alt", "")
        width = _parse_dimension(img.get("width", ""), img.get("style", ""), "width")
        height = _parse_dimension(img.get("height", ""), img.get("style", ""), "height")

        results.append(
            DocumentImage(
                node_id=_make_node_id(img),
                node_name=alt or "image",
                width=width,
                height=height,
            )
        )
    return results


def _parse_dimension(attr_value: str, style_attr: str, prop_name: str) -> float | None:
    """Parse dimension from attribute first, then inline style."""
    if attr_value:
        num = re.search(r"(\d+)", attr_value)
        if num:
            return float(num.group(1))

    style = parse_inline_style(style_attr)
    val = style.properties.get(prop_name, "")
    if val:
        return extract_font_size_px(val)
    return None


# ── Button extraction ──────────────────────────────────────────────


def _extract_buttons(element: HtmlElement) -> list[DocumentButton]:
    """Detect buttons via multiple email patterns."""
    results: list[DocumentButton] = []
    seen_hrefs: set[str] = set()

    # Pattern 1: <a> with background-color in style
    for a_tag in element.iter("a"):
        style = parse_inline_style(a_tag.get("style", ""))
        bg = style.properties.get("background-color", "") or style.properties.get("background", "")
        if bg and normalize_hex_color(bg):
            href = a_tag.get("href", "")
            text = (a_tag.text_content() or "").strip()
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            results.append(
                DocumentButton(
                    node_id=_make_node_id(a_tag),
                    text=html_mod.escape(text) if text else "Button",
                )
            )

    # Pattern 2: role="button"
    for el in element.iter():
        if not isinstance(el.tag, str):
            continue
        if el.get("role") == "button" and el.tag != "a":
            text = (el.text_content() or "").strip()
            if text:
                results.append(
                    DocumentButton(
                        node_id=_make_node_id(el),
                        text=html_mod.escape(text),
                    )
                )

    # Pattern 3: Bulletproof button — <table> with single <a> child
    for table in element.iter("table"):
        links = list(table.iter("a"))
        if len(links) == 1:
            a_tag = links[0]
            href = a_tag.get("href", "")
            if href in seen_hrefs:
                continue
            # Check if the table has bg-color (bulletproof pattern)
            table_style = parse_inline_style(table.get("style", ""))
            table_bg = table.get("bgcolor", "") or table_style.properties.get(
                "background-color", ""
            )
            if table_bg and normalize_hex_color(table_bg):
                text = (a_tag.text_content() or "").strip()
                seen_hrefs.add(href)
                results.append(
                    DocumentButton(
                        node_id=_make_node_id(table),
                        text=html_mod.escape(text) if text else "Button",
                    )
                )

    return results


# ── Column detection ───────────────────────────────────────────────


def _detect_columns(
    element: HtmlElement,
) -> tuple[str, list[DocumentColumn]]:
    """Detect column layout from ``<td>`` children or inline-block divs."""
    # Find direct <td> children (may be nested under <tr>)
    tds: list[HtmlElement] = []
    for child in element.iter("td"):
        # Only consider direct tds (not deeply nested ones)
        parent = child.getparent()
        if parent is not None and parent.tag == "tr":
            grandparent = parent.getparent()
            gp_parent = grandparent.getparent() if grandparent is not None else None
            gp_gp = gp_parent.getparent() if gp_parent is not None else None
            if grandparent is not None and (
                grandparent is element or gp_parent is element or gp_gp is element
            ):
                tds.append(child)

    # Also detect inline-block columns (fluid hybrid pattern)
    if not tds or len(tds) <= 1:
        inline_block_cols: list[HtmlElement] = []
        for child in element.iter("div"):
            style = parse_inline_style(child.get("style", ""))
            display = style.properties.get("display", "")
            if "inline-block" in display:
                inline_block_cols.append(child)
        if len(inline_block_cols) > 1:
            tds = inline_block_cols

    count = len(tds)
    if count <= 1:
        return ("single", [])

    layout = {2: "two-column", 3: "three-column"}.get(count, "multi-column")

    columns: list[DocumentColumn] = []
    for idx, td in enumerate(tds):
        col_texts = _extract_texts(td)
        col_images = _extract_images(td)
        col_buttons = _extract_buttons(td)
        width = _parse_dimension(td.get("width", ""), td.get("style", ""), "width")

        columns.append(
            DocumentColumn(
                column_idx=idx,
                node_id=_make_node_id(td),
                node_name=f"column-{idx}",
                width=width,
                texts=col_texts,
                images=col_images,
                buttons=col_buttons,
            )
        )

    return (layout, columns)


# ── Background and padding ─────────────────────────────────────────


def _extract_background(element: HtmlElement) -> str | None:
    """Extract background colour from bgcolor attribute or inline style."""
    # Check bgcolor attribute
    bgcolor = element.get("bgcolor", "")
    if bgcolor:
        return normalize_hex_color(bgcolor)

    # Check inline style
    style = parse_inline_style(element.get("style", ""))
    bg = style.properties.get("background-color", "") or style.properties.get("background", "")
    if bg:
        return normalize_hex_color(bg)

    # Check descendant <tr> and <td> for background
    for tag_name in ("tr", "td", "tbody"):
        for child in element.iter(tag_name):
            bg_attr = child.get("bgcolor", "")
            if bg_attr:
                return normalize_hex_color(bg_attr)
            child_style = parse_inline_style(child.get("style", ""))
            child_bg = child_style.properties.get(
                "background-color", ""
            ) or child_style.properties.get("background", "")
            if child_bg:
                return normalize_hex_color(child_bg)

    return None


def _extract_padding(element: HtmlElement) -> DocumentPadding | None:
    """Parse padding from inline style on the element or its first <td>."""
    targets = [element]
    for td in element.iter("td"):
        targets.append(td)
        break

    for target in targets:
        style = parse_inline_style(target.get("style", ""))
        padding_str = style.properties.get("padding", "")
        if padding_str:
            result = parse_padding_shorthand(padding_str)
            if result:
                return DocumentPadding(
                    top=result[0], right=result[1], bottom=result[2], left=result[3]
                )

        # Try individual padding properties
        top = extract_font_size_px(style.properties.get("padding-top", ""))
        right = extract_font_size_px(style.properties.get("padding-right", ""))
        bottom = extract_font_size_px(style.properties.get("padding-bottom", ""))
        left = extract_font_size_px(style.properties.get("padding-left", ""))
        if any(v is not None for v in (top, right, bottom, left)):
            return DocumentPadding(
                top=top if top is not None else 0.0,
                right=right if right is not None else 0.0,
                bottom=bottom if bottom is not None else 0.0,
                left=left if left is not None else 0.0,
            )

    return None


# ── Preheader detection ────────────────────────────────────────────


def _detect_preheader(root: HtmlElement) -> str | None:
    """Find preheader text: hidden element near top of body."""
    body = root.find(".//body")
    if body is None:
        body = root

    for child in body:
        if not isinstance(child.tag, str):
            continue
        if child.tag in ("div", "span", "p"):
            style_attr = child.get("style", "")
            if _HIDDEN_RE.search(style_attr):
                text = (child.text_content() or "").strip()
                if text:
                    return text[:500]  # Cap preheader length
        # Stop searching after first visible element
        if child.tag in ("table", "div") and not _HIDDEN_RE.search(child.get("style", "")):
            break

    return None


def _detect_charset(root: HtmlElement) -> str | None:
    """Detect charset from meta tag."""
    for meta in root.iter("meta"):
        charset = meta.get("charset")
        if charset:
            return charset
        content = meta.get("content", "")
        if "charset=" in content.lower():
            match = re.search(r"charset=([^\s;]+)", content, re.IGNORECASE)
            if match:
                return match.group(1)
    return None


# ── Utilities ──────────────────────────────────────────────────────


def _estimate_height(element: HtmlElement) -> float | None:
    """Estimate element height from style or content."""
    style = parse_inline_style(element.get("style", ""))
    h = extract_font_size_px(style.properties.get("height", ""))
    if h:
        return h
    # Count images for rough estimate
    img_count = len(list(element.iter("img")))
    text_len = len((element.text_content() or "").strip())
    if img_count == 0 and text_len == 0:
        return 0.0
    return None


def _make_node_id(element: HtmlElement) -> str:
    """Generate a deterministic node ID from element content and position."""
    existing_id = element.get("id") or element.get("data-section-id")
    if existing_id:
        return existing_id
    tag = element.tag if isinstance(element.tag, str) else "unknown"
    text = (element.text or "")[:50]
    # Use sourceline + sibling index to disambiguate same-line elements
    line = str(element.sourceline if element.sourceline is not None else 0)
    parent = element.getparent()
    sibling_idx = list(parent).index(element) if parent is not None else 0
    digest = hashlib.md5(
        f"{tag}:{text}:{line}:{sibling_idx}".encode(), usedforsecurity=False
    ).hexdigest()[:8]
    return f"html-{digest}"
