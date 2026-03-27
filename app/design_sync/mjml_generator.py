"""MJML markup generation from email layout analysis.

Pure functions — no I/O, no async. Converts DesignLayoutDescription + ExtractedTokens
into MJML markup strings that can be compiled via the Maizzle sidecar's /compile-mjml endpoint.
"""

from __future__ import annotations

import html as html_mod
from typing import TYPE_CHECKING

from app.design_sync.converter import (
    _font_stack,
    _sanitize_css_value,
    convert_colors_to_palette,
    convert_typography,
)
from app.design_sync.figma.layout_analyzer import (
    ButtonElement,
    ColumnLayout,
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
)

if TYPE_CHECKING:
    from app.design_sync.figma.layout_analyzer import DesignLayoutDescription
    from app.design_sync.protocol import ExtractedTokens
    from app.projects.design_system import BrandPalette, Typography


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_mjml(
    layout: DesignLayoutDescription,
    tokens: ExtractedTokens,
    *,
    container_width: int = 600,
) -> str:
    """Assemble a complete MJML document from layout analysis and design tokens."""
    palette = convert_colors_to_palette(tokens.colors)
    typo = convert_typography(tokens.typography)

    preheader_text = ""
    body_sections: list[EmailSection] = []
    for section in layout.sections:
        if section.section_type == EmailSectionType.PREHEADER:
            preheader_text = " ".join(t.content for t in section.texts)
        else:
            body_sections.append(section)

    head = _mjml_head(palette, typo, tokens, preheader_text, container_width)
    sections_mjml = "\n".join(
        _mjml_section(s, palette, typo, container_width) for s in body_sections
    )

    return f'<mjml>\n{head}\n<mj-body width="{container_width}px" background-color="{palette.background}">\n{sections_mjml}\n</mj-body>\n</mjml>'


# ---------------------------------------------------------------------------
# <mj-head> assembly
# ---------------------------------------------------------------------------


def _mjml_head(
    palette: BrandPalette,
    typo: Typography,
    tokens: ExtractedTokens,
    preheader_text: str,
    container_width: int,
) -> str:
    """Build the <mj-head> block with attributes, styles, and preheader."""
    body_font = _sanitize_css_value(typo.body_font) or "Arial, Helvetica, sans-serif"
    base_size = typo.base_size or "16px"
    body_lh = typo.body_line_height or "1.5"

    parts = ["<mj-head>"]

    # Global attribute defaults
    parts.append("<mj-attributes>")
    parts.append(f'<mj-all font-family="{body_font}" />')
    parts.append(
        f'<mj-text font-size="{base_size}" color="{palette.text}" line-height="{body_lh}" />'
    )
    parts.append(
        f'<mj-button background-color="{palette.primary}" color="#ffffff"'
        f' font-size="16px" inner-padding="12px 24px" border-radius="4px" />'
    )
    parts.append("</mj-attributes>")

    # Preheader
    if preheader_text:
        parts.append(f"<mj-preview>{html_mod.escape(preheader_text)}</mj-preview>")

    # Dark mode CSS
    dark_css = _dark_mode_mjml_css(tokens)
    if dark_css:
        parts.append(f"<mj-style>\n{dark_css}\n</mj-style>")

    # Responsive styles
    parts.append("<mj-style>")
    parts.append(f"  @media only screen and (max-width: {container_width}px) {{")
    parts.append("    .mobile-full-width { width: 100% !important; }")
    parts.append("  }")
    parts.append("</mj-style>")

    parts.append("</mj-head>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Dark mode CSS
# ---------------------------------------------------------------------------


def _dark_mode_mjml_css(tokens: ExtractedTokens) -> str:
    """Generate dark mode CSS for <mj-style> from token dark_colors."""
    if not tokens.dark_colors:
        return ""

    dark_by_name = {c.name.lower(): c for c in tokens.dark_colors}
    pairs: list[tuple[str, str]] = []
    for light in tokens.colors:
        dark = dark_by_name.get(light.name.lower())
        if dark:
            pairs.append((light.name.lower(), _sanitize_css_value(dark.hex) or dark.hex))

    if not pairs:
        return ""

    lines = ["@media (prefers-color-scheme: dark) {"]
    lines.append(f"  body {{ background-color: {pairs[0][1]} !important; }}")
    for i, (name, dark_hex) in enumerate(pairs):
        lines.append(f"  .dm-{i} {{ background-color: {dark_hex} !important; }}")
        if any(kw in name for kw in ("text", "body", "foreground")):
            lines.append(f"  .dm-{i}-text {{ color: {dark_hex} !important; }}")
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section rendering
# ---------------------------------------------------------------------------


def _section_padding(section: EmailSection) -> str:
    """Build padding attribute string from section fields."""
    top = int(section.padding_top) if section.padding_top else 0
    right = int(section.padding_right) if section.padding_right else 0
    bottom = int(section.padding_bottom) if section.padding_bottom else 0
    left = int(section.padding_left) if section.padding_left else 0
    if top == 0 and right == 0 and bottom == 0 and left == 0:
        return ""
    return f' padding="{top}px {right}px {bottom}px {left}px"'


def _mjml_section(
    section: EmailSection,
    palette: BrandPalette,
    typo: Typography,
    container_width: int,
) -> str:
    """Convert a single EmailSection into MJML markup."""
    st = section.section_type

    # Section comment marker for post-processing
    marker = f"<!-- section:{section.node_id}:{st.value} -->"

    if st == EmailSectionType.SPACER:
        return _mjml_spacer(section, marker)

    if st == EmailSectionType.DIVIDER:
        return _mjml_divider(section, palette, marker)

    bg_attr = ""
    if section.bg_color:
        bg_attr = f' background-color="{_sanitize_css_value(section.bg_color) or section.bg_color}"'

    padding = _section_padding(section)

    # HERO with background image
    if st == EmailSectionType.HERO:
        bg_img = next((img for img in section.images if img.is_background), None)
        if bg_img:
            bg_attr += f' background-url="{{{{img:{bg_img.node_id}}}}}"'

    inner = _mjml_columns(section, palette, typo, container_width)

    # Footer uses smaller, muted text
    if st == EmailSectionType.FOOTER:
        inner = _mjml_footer_content(section, palette)

    return f"{marker}\n<mj-section{bg_attr}{padding}>\n{inner}\n</mj-section>"


# ---------------------------------------------------------------------------
# Column structure
# ---------------------------------------------------------------------------


def _mjml_columns(
    section: EmailSection,
    palette: BrandPalette,
    typo: Typography,
    container_width: int,
) -> str:
    """Build column structure based on ColumnLayout."""
    cl = section.column_layout

    if cl == ColumnLayout.SINGLE or section.column_count <= 1:
        content = _mjml_column_content(
            section.texts, section.images, section.buttons, palette, typo
        )
        return f"<mj-column>\n{content}\n</mj-column>"

    # Multi-column: use column_groups if available, otherwise split evenly
    if section.column_groups:
        parts: list[str] = []
        for group in section.column_groups:
            if group.width and container_width > 0:
                pct = round(group.width / container_width * 100, 2)
                width_attr = f' width="{pct}%"'
            elif cl == ColumnLayout.TWO_COLUMN:
                width_attr = ' width="50%"'
            elif cl == ColumnLayout.THREE_COLUMN:
                width_attr = ' width="33.33%"'
            else:
                pct = round(100 / section.column_count, 2)
                width_attr = f' width="{pct}%"'
            content = _mjml_column_content(group.texts, group.images, group.buttons, palette, typo)
            parts.append(f"<mj-column{width_attr}>\n{content}\n</mj-column>")
        return "\n".join(parts)

    # No column_groups — equal-width columns with all content in first column
    if cl == ColumnLayout.TWO_COLUMN:
        width_attr = ' width="50%"'
        count = 2
    elif cl == ColumnLayout.THREE_COLUMN:
        width_attr = ' width="33.33%"'
        count = 3
    else:
        pct = round(100 / section.column_count, 2)
        width_attr = f' width="{pct}%"'
        count = section.column_count

    content = _mjml_column_content(section.texts, section.images, section.buttons, palette, typo)
    cols = [f"<mj-column{width_attr}>\n{content}\n</mj-column>"]
    for _ in range(count - 1):
        cols.append(f"<mj-column{width_attr}>\n</mj-column>")
    return "\n".join(cols)


# ---------------------------------------------------------------------------
# Column content assembly
# ---------------------------------------------------------------------------


def _mjml_column_content(
    texts: list[TextBlock],
    images: list[ImagePlaceholder],
    buttons: list[ButtonElement],
    palette: BrandPalette,
    typo: Typography,
) -> str:
    """Assemble content elements within a single column."""
    parts: list[str] = []
    # Non-background images first
    for img in images:
        if not img.is_background:
            parts.append(_mjml_image(img))
    # Text blocks
    for text in texts:
        parts.append(_mjml_text(text, typo, palette))
    # Buttons
    for btn in buttons:
        parts.append(_mjml_button(btn, palette))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Element renderers
# ---------------------------------------------------------------------------


def _mjml_text(text: TextBlock, typo: Typography, palette: BrandPalette) -> str:
    """Render a TextBlock as <mj-text>."""
    escaped = html_mod.escape(text.content)
    attrs: list[str] = []

    if text.is_heading:
        font = _sanitize_css_value(typo.heading_font) or typo.heading_font
        size = f"{int(text.font_size)}px" if text.font_size else "24px"
        weight = str(text.font_weight) if text.font_weight else "700"
        lh = typo.heading_line_height or "1.3"
        attrs.append(f'font-size="{size}"')
        attrs.append(f'font-weight="{weight}"')
        attrs.append(f'font-family="{font}"')
        attrs.append(f'line-height="{lh}"')
        if typo.heading_letter_spacing:
            attrs.append(f'letter-spacing="{typo.heading_letter_spacing}"')
        tag = "h2" if (text.font_size and text.font_size < 28) else "h1"
        inner = f"<{tag}>{escaped}</{tag}>"
    else:
        attrs.append(f'color="{palette.text}"')
        if text.font_size:
            attrs.append(f'font-size="{int(text.font_size)}px"')
        if text.font_weight and text.font_weight != 400:
            attrs.append(f'font-weight="{text.font_weight}"')
        if text.font_family:
            stack = _font_stack(text.font_family)
            attrs.append(f'font-family="{_sanitize_css_value(stack)}"')
        if text.line_height:
            attrs.append(f'line-height="{int(text.line_height)}px"')
        if text.letter_spacing:
            attrs.append(f'letter-spacing="{round(text.letter_spacing, 1)}px"')
        inner = f"<p>{escaped}</p>"

    attr_str = " " + " ".join(attrs) if attrs else ""
    return f"<mj-text{attr_str}>{inner}</mj-text>"


def _mjml_image(img: ImagePlaceholder) -> str:
    """Render an ImagePlaceholder as <mj-image>."""
    src = f"{{{{img:{img.node_id}}}}}"
    alt = html_mod.escape(img.node_name)
    attrs = [f'src="{src}"', f'alt="{alt}"']
    if img.width:
        attrs.append(f'width="{int(img.width)}px"')
    if img.height:
        attrs.append(f'height="{int(img.height)}px"')
    attr_str = " ".join(attrs)
    return f"<mj-image {attr_str} />"


def _mjml_button(btn: ButtonElement, palette: BrandPalette) -> str:
    """Render a ButtonElement as <mj-button>."""
    text = html_mod.escape(btn.text)
    attrs = [
        'href="#"',
        f'background-color="{palette.primary}"',
        f'color="{palette.background}"',
    ]
    if btn.width:
        attrs.append(f'width="{int(btn.width)}px"')
    attr_str = " ".join(attrs)
    return f"<mj-button {attr_str}>{text}</mj-button>"


# ---------------------------------------------------------------------------
# Special section types
# ---------------------------------------------------------------------------


def _mjml_spacer(section: EmailSection, marker: str) -> str:
    """Render a SPACER section."""
    height = int(section.height) if section.height else 20
    return f'{marker}\n<mj-section><mj-column><mj-spacer height="{height}px" /></mj-column></mj-section>'


def _mjml_divider(section: EmailSection, palette: BrandPalette, marker: str) -> str:
    """Render a DIVIDER section."""
    padding = _section_padding(section)
    return (
        f"{marker}\n<mj-section{padding}><mj-column>"
        f'<mj-divider border-color="{palette.secondary}" border-width="1px" />'
        f"</mj-column></mj-section>"
    )


def _mjml_footer_content(
    section: EmailSection,
    palette: BrandPalette,
) -> str:
    """Render footer content with muted styling."""
    parts: list[str] = []
    muted_color = palette.secondary
    small_size = "12px"

    for text in section.texts:
        escaped = html_mod.escape(text.content)
        parts.append(
            f'<mj-text font-size="{small_size}" color="{muted_color}"'
            f' align="center"><p>{escaped}</p></mj-text>'
        )
    for img in section.images:
        if not img.is_background:
            parts.append(_mjml_image(img))

    if not parts:
        parts.append(
            f'<mj-text font-size="{small_size}" color="{muted_color}"'
            f' align="center"><p>&copy; Company Name</p></mj-text>'
        )

    content = "\n".join(parts)
    return f"<mj-column>\n{content}\n</mj-column>"


# ---------------------------------------------------------------------------
# Post-processing: inject data attributes into compiled HTML
# ---------------------------------------------------------------------------


def inject_section_markers(compiled_html: str, layout: DesignLayoutDescription) -> str:
    """Replace MJML comment markers with data attributes on the nearest table.

    MJML strips data-* attributes during compilation, so we inject comment markers
    in the MJML source and then replace them in the compiled HTML with proper
    data attributes on the enclosing <table> element.
    """
    result = compiled_html
    for section in layout.sections:
        if section.section_type == EmailSectionType.PREHEADER:
            continue
        marker = f"<!-- section:{section.node_id}:{section.section_type.value} -->"
        replacement = (
            f"<!-- section:{section.node_id}:{section.section_type.value} -->"
            f'\n<div data-section-type="{section.section_type.value}"'
            f' data-node-id="{html_mod.escape(section.node_id)}">'
        )
        marker_idx = result.find(marker)
        if marker_idx >= 0:
            result = result[:marker_idx] + replacement + result[marker_idx + len(marker) :]
            # Close the wrapper div after the section's table
            table_end = result.find("</table>", marker_idx + len(replacement))
            if table_end >= 0:
                insert_pos = table_end + len("</table>")
                result = result[:insert_pos] + "\n</div>" + result[insert_pos:]
    return result
