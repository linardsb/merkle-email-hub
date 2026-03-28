"""Parse ``<mj-body>`` children into ``DocumentSection`` list."""

from __future__ import annotations

import urllib.parse
import uuid

from lxml import etree

from app.design_sync.email_design_document import (
    DocumentButton,
    DocumentColumn,
    DocumentImage,
    DocumentPadding,
    DocumentSection,
    DocumentText,
)

# ── Constants ────────────────────────────────────────────────────────

_SAFE_URL_SCHEMES = frozenset({"http", "https"})


# ── Public API ───────────────────────────────────────────────────────


def parse_sections(body: etree._Element) -> list[DocumentSection]:
    """Walk ``<mj-body>`` children and return a flat list of sections."""
    sections: list[DocumentSection] = []
    y_pos = 0.0
    for child in body:
        tag = _local_tag(child)
        if tag == "mj-section":
            sections.append(_parse_section(child, y_pos))
            y_pos += _section_height(sections[-1])
        elif tag == "mj-hero":
            sections.append(_parse_hero(child, y_pos))
            y_pos += _section_height(sections[-1])
        elif tag == "mj-wrapper":
            # Unwrap — recurse into children
            for inner in child:
                inner_tag = _local_tag(inner)
                if inner_tag == "mj-section":
                    sections.append(_parse_section(inner, y_pos))
                    y_pos += _section_height(sections[-1])
                elif inner_tag == "mj-hero":
                    sections.append(_parse_hero(inner, y_pos))
                    y_pos += _section_height(sections[-1])
    return sections


# ── Section parsers ──────────────────────────────────────────────────


def _parse_section(el: etree._Element, y_pos: float) -> DocumentSection:
    columns_el = el.findall("mj-column")
    col_count = len(columns_el)

    if col_count <= 1:
        layout = "single"
    elif col_count == 2:
        layout = "two-column"
    elif col_count == 3:
        layout = "three-column"
    else:
        layout = "multi-column"

    # Collect section-level content (non-column children)
    all_texts: list[DocumentText] = []
    all_images: list[DocumentImage] = []
    all_buttons: list[DocumentButton] = []
    doc_columns: list[DocumentColumn] = []

    # Check for direct children that aren't columns (e.g. standalone mj-spacer, mj-divider)
    has_only_spacer = False
    has_only_divider = False
    spacer_height: float | None = None

    for child in el:
        tag = _local_tag(child)
        if tag == "mj-spacer" and col_count == 0:
            has_only_spacer = True
            spacer_height = _parse_float(child.get("height"))
        elif tag == "mj-divider" and col_count == 0:
            has_only_divider = True

    if has_only_spacer:
        return DocumentSection(
            id=_gen_id(),
            type="spacer",
            y_position=y_pos,
            height=spacer_height,
            padding=_parse_padding(el.get("padding")),
            background_color=el.get("background-color"),
        )

    if has_only_divider:
        return DocumentSection(
            id=_gen_id(),
            type="divider",
            y_position=y_pos,
            padding=_parse_padding(el.get("padding")),
            background_color=el.get("background-color"),
        )

    # Parse columns
    for idx, col_el in enumerate(columns_el):
        col_texts, col_images, col_buttons = _parse_column_content(col_el)
        all_texts.extend(col_texts)
        all_images.extend(col_images)
        all_buttons.extend(col_buttons)

        width_pct = _parse_width_pct(col_el.get("width"))
        doc_columns.append(
            DocumentColumn(
                column_idx=idx,
                node_id=_gen_id(),
                node_name=f"column-{idx}",
                width=width_pct,
                texts=col_texts,
                images=col_images,
                buttons=col_buttons,
            )
        )

    # Detect social / nav sections from column content
    section_type = "unknown"
    content_roles: list[str] = []
    for child in el:
        tag = _local_tag(child)
        if tag == "mj-social":
            section_type = "social"
            content_roles.append("social_links")
            # Extract social elements as images
            for social_el in child.findall("mj-social-element"):
                src = social_el.get("src")
                if src and _validate_url(src):
                    all_images.append(
                        DocumentImage(
                            node_id=_gen_id(),
                            node_name=social_el.get("name", "social-icon"),
                        )
                    )
        elif tag == "mj-navbar":
            section_type = "nav"
            for link_el in child.findall("mj-navbar-link"):
                text = (link_el.text or "").strip()
                if text:
                    all_texts.append(DocumentText(node_id=_gen_id(), content=text))

    return DocumentSection(
        id=_gen_id(),
        type=section_type,
        y_position=y_pos,
        column_layout=layout,
        column_count=max(col_count, 1),
        padding=_parse_padding(el.get("padding")),
        background_color=el.get("background-color"),
        texts=all_texts,
        images=all_images,
        buttons=all_buttons,
        columns=doc_columns if col_count > 1 else [],
        content_roles=content_roles,
    )


def _parse_hero(el: etree._Element, y_pos: float) -> DocumentSection:
    texts: list[DocumentText] = []
    images: list[DocumentImage] = []
    buttons: list[DocumentButton] = []

    # Hero background image
    bg_url = el.get("background-url")
    if bg_url and _validate_url(bg_url):
        images.append(
            DocumentImage(
                node_id=_gen_id(),
                node_name="hero-bg",
                width=_parse_float(el.get("background-width")),
                height=_parse_float(el.get("background-height")),
                is_background=True,
            )
        )

    # Parse inner content (hero can have direct children or mj-column)
    for child in el:
        tag = _local_tag(child)
        if tag == "mj-column":
            col_texts, col_images, col_buttons = _parse_column_content(child)
            texts.extend(col_texts)
            images.extend(col_images)
            buttons.extend(col_buttons)
        elif tag == "mj-text":
            texts.extend(_parse_text_element(child))
        elif tag == "mj-image":
            img = _parse_image_element(child)
            if img is not None:
                images.append(img)
        elif tag == "mj-button":
            btn = _parse_button_element(child)
            if btn is not None:
                buttons.append(btn)

    return DocumentSection(
        id=_gen_id(),
        type="hero",
        y_position=y_pos,
        padding=_parse_padding(el.get("padding")),
        background_color=el.get("background-color"),
        texts=texts,
        images=images,
        buttons=buttons,
    )


# ── Column content parser ────────────────────────────────────────────


def _parse_column_content(
    col_el: etree._Element,
) -> tuple[list[DocumentText], list[DocumentImage], list[DocumentButton]]:
    texts: list[DocumentText] = []
    images: list[DocumentImage] = []
    buttons: list[DocumentButton] = []

    for child in col_el:
        tag = _local_tag(child)
        if tag == "mj-text":
            texts.extend(_parse_text_element(child))
        elif tag == "mj-image":
            img = _parse_image_element(child)
            if img is not None:
                images.append(img)
        elif tag == "mj-button":
            btn = _parse_button_element(child)
            if btn is not None:
                buttons.append(btn)
        elif tag == "mj-spacer":
            pass  # spacers inside columns are layout hints, skip
        elif tag == "mj-divider":
            pass  # dividers inside columns are visual, skip

    return texts, images, buttons


# ── Element parsers ──────────────────────────────────────────────────


def _parse_text_element(el: etree._Element) -> list[DocumentText]:
    """Extract text blocks from ``<mj-text>`` inner HTML."""
    results: list[DocumentText] = []

    # Get base typography from element attributes
    base_font_size = _parse_float(el.get("font-size")) or None
    base_font_family = el.get("font-family")
    base_font_weight = _parse_int(el.get("font-weight"))
    base_line_height = _parse_float(el.get("line-height")) or None
    base_letter_spacing = _parse_float(el.get("letter-spacing")) or None

    # Get inner HTML content
    inner_html = _inner_html(el)
    if not inner_html.strip():
        return results

    # Check for heading tags in inner HTML
    heading_found = False
    for heading_tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        for heading_el in el.iter(heading_tag):
            heading_found = True
            text_content = etree.tostring(heading_el, method="text", encoding="unicode").strip()
            if text_content:
                results.append(
                    DocumentText(
                        node_id=_gen_id(),
                        content=text_content,
                        font_size=base_font_size,
                        is_heading=True,
                        font_family=base_font_family,
                        font_weight=base_font_weight if base_font_weight is not None else 700,
                        line_height=base_line_height,
                        letter_spacing=base_letter_spacing,
                    )
                )

    # If no headings, extract all text content as a single block
    if not heading_found:
        text_content = etree.tostring(el, method="text", encoding="unicode").strip()
        if text_content:
            results.append(
                DocumentText(
                    node_id=_gen_id(),
                    content=text_content,
                    font_size=base_font_size,
                    is_heading=False,
                    font_family=base_font_family,
                    font_weight=base_font_weight,
                    line_height=base_line_height,
                    letter_spacing=base_letter_spacing,
                )
            )

    return results


def _parse_image_element(el: etree._Element) -> DocumentImage | None:
    src = el.get("src", "")
    if not _validate_url(src):
        return None
    return DocumentImage(
        node_id=_gen_id(),
        node_name=el.get("alt") or el.get("title") or "image",
        width=_parse_float(el.get("width")),
        height=_parse_float(el.get("height")),
    )


def _parse_button_element(el: etree._Element) -> DocumentButton | None:
    text = etree.tostring(el, method="text", encoding="unicode").strip()
    if not text:
        return None
    return DocumentButton(
        node_id=_gen_id(),
        text=text,
        width=_parse_float(el.get("width")),
        height=_parse_float(el.get("height")),
    )


# ── Helpers ──────────────────────────────────────────────────────────


def _local_tag(el: etree._Element) -> str:
    tag = el.tag
    if isinstance(tag, str) and "}" in tag:
        return tag.split("}", 1)[1]
    return str(tag)


def _gen_id() -> str:
    return uuid.uuid4().hex[:12]


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace("px", "").replace("%", "").replace("em", "").strip())
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_width_pct(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace("%", "").replace("px", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_padding(padding_str: str | None) -> DocumentPadding | None:
    if not padding_str:
        return None
    parts = padding_str.replace("px", "").split()
    try:
        values = [float(p) for p in parts]
    except ValueError:
        return None

    if len(values) == 1:
        return DocumentPadding(top=values[0], right=values[0], bottom=values[0], left=values[0])
    if len(values) == 2:
        return DocumentPadding(top=values[0], right=values[1], bottom=values[0], left=values[1])
    if len(values) == 4:
        return DocumentPadding(top=values[0], right=values[1], bottom=values[2], left=values[3])
    return None


def _validate_url(url: str) -> bool:
    if not url:
        return False
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in _SAFE_URL_SCHEMES


def _inner_html(el: etree._Element) -> str:
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    for child in el:
        parts.append(etree.tostring(child, encoding="unicode"))
    return "".join(parts)


def _section_height(section: DocumentSection) -> float:
    return section.height if section.height is not None else 100.0
