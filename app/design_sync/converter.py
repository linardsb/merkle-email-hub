"""Convert design elements to email-safe HTML and design system tokens (provider-agnostic)."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from app.core.logging import get_logger
from app.design_sync.protocol import (
    DesignNode,
    DesignNodeType,
    ExtractedColor,
    ExtractedGradient,
    ExtractedSpacing,
    ExtractedTypography,
)
from app.projects.design_system import BrandPalette, Typography

if TYPE_CHECKING:
    from app.design_sync.compatibility import ConverterCompatibility
    from app.design_sync.figma.layout_analyzer import EmailSection, TextBlock

logger = get_logger(__name__)

# ── YAML-backed font fallback data ──
_FONT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "email_client_fonts.yaml"
_FONT_DATA: dict[str, Any] = (
    yaml.safe_load(_FONT_DATA_PATH.read_text()) if _FONT_DATA_PATH.exists() else {}
)
_FALLBACK_MAP: dict[str, list[str]] = _FONT_DATA.get("fallback_map", {})

# Figma text property maps
_TEXT_CASE_MAP: dict[str, str] = {
    "UPPER": "uppercase",
    "LOWER": "lowercase",
    "TITLE": "capitalize",
}
_TEXT_DEC_MAP: dict[str, str] = {"UNDERLINE": "underline", "STRIKETHROUGH": "line-through"}

# Design node type → HTML element mapping for email
_NODE_HTML_MAP: dict[DesignNodeType, str] = {
    DesignNodeType.FRAME: "table",
    DesignNodeType.TEXT: "td",
    DesignNodeType.IMAGE: "img",
    DesignNodeType.GROUP: "table",
    # VECTOR: skipped — vectors/SVGs are not email-safe (returns "" below)
}


@dataclass(frozen=True)
class _NodeProps:
    """Supplementary visual properties not carried by DesignNode."""

    bg_color: str | None = None
    font_family: str | None = None
    font_size: float | None = None
    font_weight: str | None = None
    padding_top: float = 0
    padding_right: float = 0
    padding_bottom: float = 0
    padding_left: float = 0
    border_color: str | None = None
    border_width: float = 0
    layout_direction: str | None = None  # "row" | "column" | None
    item_spacing: float = 0
    counter_axis_spacing: float = 0
    line_height_px: float | None = None
    letter_spacing_px: float | None = None
    text_transform: str | None = None
    text_decoration: str | None = None


def _sanitize_css_value(value: str) -> str:
    """Strip characters that could break out of a CSS property value.

    Removes semicolons, braces, angle brackets, and other injection vectors.
    Returns empty string if the value is entirely unsafe.
    """
    # Remove anything that could terminate a style attribute or inject HTML
    sanitized = re.sub(r'[;<>{}\'"\\()]+', "", value)
    return sanitized.strip()


def _relative_luminance(hex_color: str) -> float:
    """Calculate relative luminance of a hex color (0=black, 1=white)."""
    hex_clean = hex_color.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    if len(hex_clean) != 6:
        return 0.0
    try:
        r, g, b = int(hex_clean[0:2], 16), int(hex_clean[2:4], 16), int(hex_clean[4:6], 16)
    except ValueError:
        return 0.0

    def _linearize(val: int) -> float:
        srgb = val / 255.0
        return srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4

    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _contrast_ratio(lum1: float, lum2: float) -> float:
    """WCAG contrast ratio between two luminances."""
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def convert_colors_to_palette(colors: list[ExtractedColor]) -> BrandPalette:
    """Map extracted design colors to BrandPalette.

    Heuristic: match color names to palette roles (primary, secondary, accent,
    background, text, link). Falls back to positional assignment.
    Ensures adequate contrast between text and background.
    """
    role_map: dict[str, str] = {}
    name_hints: dict[str, list[str]] = {
        "primary": ["primary", "brand", "main"],
        "secondary": ["secondary", "accent-2"],
        "accent": ["accent", "highlight", "cta"],
        "background": ["background", "bg", "surface"],
        "text": ["text", "body", "foreground", "fg"],
        "link": ["link", "url", "anchor"],
    }

    # Name-based matching
    for color in colors:
        lower_name = color.name.lower()
        for role, hints in name_hints.items():
            if role not in role_map and any(h in lower_name for h in hints):
                role_map[role] = color.hex
                break

    # Positional fallback for unfilled roles
    unmatched = [c for c in colors if c.hex not in role_map.values()]
    for role in ("primary", "secondary", "accent"):
        if role not in role_map and unmatched:
            role_map[role] = unmatched.pop(0).hex

    # Ensure text/background contrast meets WCAG AA minimum (3:1)
    bg_hex = role_map.get("background", "#ffffff")
    text_hex = role_map.get("text", "#000000")
    bg_lum = _relative_luminance(bg_hex)
    text_lum = _relative_luminance(text_hex)
    if _contrast_ratio(bg_lum, text_lum) < 3.0:
        role_map["text"] = "#ffffff" if bg_lum < 0.5 else "#000000"
        logger.info(
            "design_sync.contrast_fix",
            bg=bg_hex,
            original_text=text_hex,
            fixed_text=role_map["text"],
        )

    # Ensure link color also has adequate contrast against background
    link_hex = role_map.get("link", "#0000ee")
    link_lum = _relative_luminance(link_hex)
    if _contrast_ratio(bg_lum, link_lum) < 3.0:
        role_map["link"] = "#99ccff" if bg_lum < 0.5 else "#0000ee"

    return BrandPalette(
        primary=role_map.get("primary", "#333333"),
        secondary=role_map.get("secondary", "#666666"),
        accent=role_map.get("accent", "#0066cc"),
        background=role_map.get("background", "#ffffff"),
        text=role_map.get("text", "#000000"),
        link=role_map.get("link", "#0000ee"),
    )


def _font_stack(family: str) -> str:
    """Build email-safe CSS font stack using data/email_client_fonts.yaml."""
    family_clean = family.strip("'\"").strip()
    if "," in family_clean:
        return family_clean
    # Look up YAML fallback map (case-insensitive)
    for mapped_name, chain in _FALLBACK_MAP.items():
        if mapped_name.strip("'\"").lower() == family_clean.lower():
            return f"{family_clean}, {', '.join(str(f) for f in chain)}"
    # Generic family keywords
    if family_clean.lower() in {"sans-serif", "serif", "monospace", "cursive", "fantasy"}:
        return family_clean
    # Unknown font — default sans-serif chain
    return f"{family_clean}, Arial, Helvetica, sans-serif"


def convert_typography(styles: list[ExtractedTypography]) -> Typography:
    """Map extracted typography to Typography design system model.

    Heuristic: largest font_size → heading, most common family → body.
    """
    if not styles:
        return Typography()

    # Heading: style with largest size or name containing "heading"/"title"
    heading_style = None
    for s in styles:
        if any(kw in s.name.lower() for kw in ("heading", "title", "h1", "h2")):
            heading_style = s
            break
    if heading_style is None:
        heading_style = max(styles, key=lambda s: s.size)

    # Body: style with name containing "body"/"paragraph"/"text", or smallest
    body_style = None
    for s in styles:
        if any(kw in s.name.lower() for kw in ("body", "paragraph", "text", "regular")):
            body_style = s
            break
    if body_style is None:
        body_style = min(styles, key=lambda s: s.size)

    def _px_or_none(val: float | None) -> str | None:
        if val is None:
            return None
        return f"{round(val)}px"

    def _spacing_px_or_none(val: float | None) -> str | None:
        if val is None or val == 0.0:
            return None
        return f"{round(val, 1)}px"

    return Typography(
        heading_font=_font_stack(heading_style.family),
        body_font=_font_stack(body_style.family),
        base_size=f"{int(body_style.size)}px",
        heading_line_height=_px_or_none(heading_style.line_height),
        body_line_height=_px_or_none(body_style.line_height),
        heading_letter_spacing=_spacing_px_or_none(heading_style.letter_spacing),
        body_letter_spacing=_spacing_px_or_none(body_style.letter_spacing),
        heading_text_transform=heading_style.text_transform,
    )


# Standard spacing scale — values that align to 4px/8px multiples get named
_SPACING_SCALE: dict[int, str] = {
    4: "2xs",
    8: "xs",
    12: "sm",
    16: "md",
    20: "md-lg",
    24: "lg",
    32: "xl",
    40: "xl-2",
    48: "2xl",
    64: "3xl",
}


def convert_spacing(spacing: list[ExtractedSpacing]) -> dict[str, float]:
    """Convert extracted spacing tokens to a named spacing scale.

    Maps numeric spacing values to semantic names. Values that align to
    the standard 4px/8px scale get standard names (xs, sm, md, lg, xl).
    Non-standard values keep their original name.

    Returns:
        Mapping of semantic name → pixel value.
    """
    result: dict[str, float] = {}
    for token in spacing:
        px = token.value
        int_px = int(px)
        # Use standard scale name if value matches
        if int_px in _SPACING_SCALE:
            name = _SPACING_SCALE[int_px]
        else:
            # Normalize name: strip "spacing-" prefix, lowercase
            name = token.name.lower().removeprefix("spacing-").removeprefix("space-")
            if not name:
                name = f"{int_px}px"
        # Avoid overwriting a scale entry with a different value
        if name not in result:
            result[name] = px
    return result


def _contrasting_text_color(bg_hex: str) -> str:
    """Return white or black text depending on background luminance."""
    return "#ffffff" if _relative_luminance(bg_hex) < 0.5 else "#000000"


def _gradient_to_css(gradient: ExtractedGradient) -> str:
    """Convert ExtractedGradient to CSS linear-gradient() value."""
    stops_css = ", ".join(
        f"{_sanitize_css_value(hex_val)} {round(pos * 100, 1)}%" for hex_val, pos in gradient.stops
    )
    return f"linear-gradient({gradient.angle}deg, {stops_css})"


def _determine_heading_level(
    font_size: float,
    body_font_size: float,
) -> int | None:
    """Return heading level (1-3) based on font size ratio, or None for body text."""
    if body_font_size <= 0:
        return None
    ratio = font_size / body_font_size
    if ratio >= 2.0:
        return 1
    if ratio >= 1.5:
        return 2
    if ratio >= 1.2:
        return 3
    return None


def _next_slot_name(counter: dict[str, int], slot_type: str) -> str:
    """Generate unique slot name: 'body', 'body_2', 'body_3', etc."""
    count = counter.get(slot_type, 0) + 1
    counter[slot_type] = count
    return slot_type if count == 1 else f"{slot_type}_{count}"


def _render_semantic_text(
    *,
    content: str,
    font_family: str,
    extra_style: str,
    mso_alt: str,
    pad: str,
    is_heading: bool,
    heading_level: int | None,
    slot_counter: dict[str, int] | None = None,
) -> str:
    """Render a TEXT node as semantic HTML (<h1>-<h3> or <p>) inside <td>."""
    if is_heading and heading_level is not None:
        tag = f"h{heading_level}"
        slot_attr = ""
        if slot_counter is not None:
            slot_attr = f' data-slot-name="{_next_slot_name(slot_counter, "heading")}"'
        inner_style = f"margin:0;font-family:{font_family};{mso_alt}{extra_style}"
        return f'{pad}<td><{tag}{slot_attr} style="{inner_style}">{content}</{tag}></td>'

    # Body text -> <p> (split multi-line on \n)
    lines = content.split("\n") if "\n" in content else [content]
    if len(lines) == 1:
        slot_attr = ""
        if slot_counter is not None:
            slot_attr = f' data-slot-name="{_next_slot_name(slot_counter, "body")}"'
        p_style = f"margin:0 0 10px 0;font-family:{font_family};{mso_alt}{extra_style}"
        return f'{pad}<td><p{slot_attr} style="{p_style}">{content}</p></td>'

    # Multi-line -> multiple <p> tags
    p_style = f"margin:0 0 10px 0;font-family:{font_family};{mso_alt}{extra_style}"
    p_parts: list[str] = []
    for line in lines:
        if line.strip():
            slot_attr = ""
            if slot_counter is not None:
                slot_attr = f' data-slot-name="{_next_slot_name(slot_counter, "body")}"'
            p_parts.append(f'<p{slot_attr} style="{p_style}">{line}</p>')
    inner = "".join(p_parts)
    return f"{pad}<td>{inner}</td>"


def _validate_button_contrast(
    bg_hex: str,
    text_hex: str,
    font_size_px: int,
) -> None:
    """Log a warning if button text/background contrast is below WCAG AA."""
    try:
        bg_lum = _relative_luminance(bg_hex)
        text_lum = _relative_luminance(text_hex)
        ratio = _contrast_ratio(bg_lum, text_lum)
    except (ValueError, TypeError):
        return
    threshold = 3.0 if font_size_px >= 18 else 4.5
    if ratio < threshold:
        logger.warning(
            "design_sync.button_contrast_low",
            bg=bg_hex,
            text=text_hex,
            ratio=round(ratio, 2),
            threshold=threshold,
        )


def _render_button(
    node: DesignNode,
    *,
    pad: str,
    props: _NodeProps | None,
    slot_counter: dict[str, int] | None = None,
) -> str:
    """Render a button-like COMPONENT/FRAME as a bulletproof <a> with VML fallback."""
    text_children = [c for c in node.children if c.type == DesignNodeType.TEXT and c.text_content]
    if not text_children:
        return ""
    button_text = html.escape(text_children[0].text_content or "")

    width = int(node.width) if node.width else 200
    height = max(int(node.height) if node.height else 44, 44)

    bg_color = node.fill_color or (props.bg_color if props else None) or "#0066cc"
    bg_color = _sanitize_css_value(bg_color) or "#0066cc"

    text_color = text_children[0].text_color or _contrasting_text_color(bg_color)
    text_color = _sanitize_css_value(text_color) or "#ffffff"

    font_family = "Arial,Helvetica,sans-serif"
    child_props_font = text_children[0].font_family
    if child_props_font:
        font_family = _font_stack(_sanitize_css_value(child_props_font) or "Arial")

    font_size = int(text_children[0].font_size or 16)

    _validate_button_contrast(bg_color, text_color, font_size)

    border_radius = "4px"
    shortest_side = min(width, height)
    arcsize_pct = round((4 / shortest_side) * 100) if shortest_side > 0 else 8

    v_pad = max(8, (height - font_size) // 2)
    h_pad = 24

    slot_attr = ""
    if slot_counter is not None:
        slot_attr = f' data-slot-name="{_next_slot_name(slot_counter, "cta")}"'

    parts = [
        f'{pad}<td align="center">',
        (
            f"{pad}  "
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"'
            ' style="border-collapse:collapse;'
            'mso-table-lspace:0pt;mso-table-rspace:0pt;">'
        ),
        f"{pad}    <tr>",
        (f'{pad}      <td style="border-radius:{border_radius};background-color:{bg_color};">'),
        (
            f'{pad}        <a href="#"{slot_attr} style="display:inline-block;'
            f"padding:{v_pad}px {h_pad}px;"
            f"font-family:{font_family};font-size:{font_size}px;"
            f"color:{text_color};text-decoration:none;"
            f'mso-line-height-rule:exactly;">{button_text}</a>'
        ),
        f"{pad}      </td>",
        f"{pad}    </tr>",
        f"{pad}  </table>",
        f"{pad}  <!--[if mso]>",
        (
            f'{pad}  <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"'
            f' style="width:{width}px;height:{height}px;"'
            f' arcsize="{arcsize_pct}%"'
            f' fillcolor="{bg_color}" stroke="f">'
        ),
        (f'{pad}    <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">'),
        (
            f'{pad}      <center style="font-family:Arial,sans-serif;'
            f"font-size:{font_size}px;"
            f'color:{text_color};">{button_text}</center>'
        ),
        f"{pad}    </v:textbox>",
        f"{pad}  </v:roundrect>",
        f"{pad}  <![endif]-->",
        f"{pad}</td>",
    ]
    return "\n".join(parts)


def node_to_email_html(
    node: DesignNode,
    *,
    indent: int = 0,
    props_map: dict[str, _NodeProps] | None = None,
    parent_bg: str | None = None,
    parent_font: str | None = None,
    section_map: dict[str, EmailSection] | None = None,
    button_ids: set[str] | None = None,
    text_meta: dict[str, TextBlock] | None = None,
    current_section: EmailSection | None = None,
    body_font_size: float = 16.0,
    compat: ConverterCompatibility | None = None,
    gradients_map: dict[str, ExtractedGradient] | None = None,
    _depth: int = 0,
    container_width: int = 600,
    slot_counter: dict[str, int] | None = None,
) -> str:
    """Convert a DesignNode tree to email-safe HTML (table layout).

    Converts flex/grid frames to table rows/cells.
    This produces a structural skeleton — the Scaffolder fills content.

    Args:
        node: The design node to convert.
        indent: Current indentation level.
        props_map: Optional supplementary visual properties keyed by node ID.
        parent_bg: Inherited background color from parent frame for contrast.
        parent_font: Inherited font-family from parent frame for inline styles.
        section_map: Node ID → EmailSection from layout analysis.
        button_ids: Node IDs identified as buttons by layout analysis.
        text_meta: Node ID → TextBlock metadata from layout analysis.
        current_section: The enclosing EmailSection (for context propagation).
        body_font_size: Base body font size in px (default 16).
        compat: Compatibility checker for client-aware warnings.
        gradients_map: Node name → ExtractedGradient for gradient CSS.
        _depth: Internal nesting depth counter for guard.
        container_width: Available width in px for column calculations.
        slot_counter: Shared per-section counter for unique data-slot-name attrs.
    """
    pad = "  " * indent
    props = props_map.get(node.id) if props_map else None

    if node.type == DesignNodeType.TEXT:
        content = html.escape(node.text_content or "")
        font_family = parent_font or "Arial,Helvetica,sans-serif"
        extra_style = ""
        if props:
            if props.font_family:
                safe_family = _sanitize_css_value(props.font_family)
                if safe_family:
                    font_family = _font_stack(safe_family)
            if props.font_size:
                extra_style += f"font-size:{int(props.font_size)}px;"
            if props.font_weight:
                # Map to email-safe weight: >=500 → bold, <500 → normal
                try:
                    weight_num = int(props.font_weight)
                    mapped = "bold" if weight_num >= 500 else "normal"
                except (ValueError, TypeError):
                    mapped = "bold" if str(props.font_weight).lower() == "bold" else "normal"
                extra_style += f"font-weight:{mapped};"
            if props.line_height_px:
                lh = round(props.line_height_px)
                extra_style += f"line-height:{lh}px;mso-line-height-rule:exactly;"
            if props.letter_spacing_px:
                if compat:
                    compat.check_and_warn(
                        "letter-spacing",
                        context=f"Text node '{node.name}'",
                    )
                ls = round(props.letter_spacing_px, 1)
                extra_style += f"letter-spacing:{ls}px;"
            if props.text_transform:
                extra_style += f"text-transform:{_sanitize_css_value(props.text_transform)};"
            if props.text_decoration:
                extra_style += f"text-decoration:{_sanitize_css_value(props.text_decoration)};"
        # Color priority: node.text_color (from design) > contrast auto > none
        if node.text_color:
            safe_text_color = _sanitize_css_value(node.text_color)
            if safe_text_color:
                extra_style += f"color:{safe_text_color};"
        elif parent_bg:
            extra_style += f"color:{_contrasting_text_color(parent_bg)};"
        # MSO font-alt for Outlook fallback
        mso_alt = ""
        if font_family:
            primary = font_family.split(",")[0].strip().strip("'\"")
            for mapped_name, chain in _FALLBACK_MAP.items():
                if mapped_name.strip("'\"").lower() == primary.lower() and chain:
                    mso_alt = f"mso-font-alt:{chain[0]};"
                    break
        # Safety net: ensure mso-line-height-rule if line-height added without it
        if "line-height:" in extra_style and "mso-line-height-rule" not in extra_style:
            extra_style += "mso-line-height-rule:exactly;"

        # Determine semantic role from layout analysis
        is_heading = False
        heading_level: int | None = None
        if text_meta and node.id in text_meta:
            tb = text_meta[node.id]
            is_heading = tb.is_heading
        if is_heading:
            font_size_val = (props.font_size if props else None) or node.font_size or 16.0
            heading_level = _determine_heading_level(font_size_val, body_font_size)
            if heading_level is None:
                # is_heading from analyzer but ratio too small — default h3
                heading_level = 3

        return _render_semantic_text(
            content=content,
            font_family=font_family,
            extra_style=extra_style,
            mso_alt=mso_alt,
            pad=pad,
            is_heading=is_heading,
            heading_level=heading_level,
            slot_counter=slot_counter,
        )

    if node.type == DesignNodeType.IMAGE:
        w_val = int(node.width) if node.width else None
        h_val = int(node.height) if node.height else None
        w = f' width="{w_val}"' if w_val else ""
        h = f' height="{h_val}"' if h_val else ""
        alt = html.escape(node.name or "")
        node_id_attr = f' data-node-id="{html.escape(node.id)}"'
        slot_attr = ""
        if slot_counter is not None:
            slot_attr = f' data-slot-name="{_next_slot_name(slot_counter, "image")}"'
        max_w = f"max-width:{w_val}px;" if w_val else ""
        return (
            f'{pad}<img src="" alt="{alt}"{node_id_attr}{slot_attr}{w}{h}'
            f' style="display:block;border:0;outline:none;text-decoration:none;'
            f'-ms-interpolation-mode:bicubic;width:100%;{max_w}height:auto;" />'
        )

    # Button detection: node is in button_ids from layout analysis
    if button_ids and node.id in button_ids:
        return _render_button(
            node,
            pad=pad,
            props=props,
            slot_counter=slot_counter,
        )

    # Frame/Group/Component/Instance → table with rows
    if node.type in (
        DesignNodeType.FRAME,
        DesignNodeType.GROUP,
        DesignNodeType.COMPONENT,
        DesignNodeType.INSTANCE,
    ):
        # Look up section data from layout analysis
        section = current_section
        if section_map and node.id in section_map:
            section = section_map[node.id]

        # Nested frames use 100% to fill parent; the converter_service wraps
        # top-level frames in <tr><td>, so 100% is correct at every level.
        width_attr = ' width="100%"'
        bgcolor_attr = ""
        # MSO reset styles on every <table>
        style_parts: list[str] = [
            "border-collapse:collapse",
            "mso-table-lspace:0pt",
            "mso-table-rspace:0pt",
        ]
        # Track the effective background for child text contrast
        effective_bg = parent_bg

        # Priority: node.fill_color (from design tool) first
        if node.fill_color:
            bgcolor_attr = f' bgcolor="{html.escape(node.fill_color)}"'
            effective_bg = node.fill_color
        # props_map overrides if present (backward compat with Penpot raw data)
        if props and props.bg_color:
            bgcolor_attr = f' bgcolor="{html.escape(props.bg_color)}"'
            effective_bg = props.bg_color

        # Gradient override: if node name matches a gradient, add CSS background
        if gradients_map and node.name in gradients_map:
            grad = gradients_map[node.name]
            gradient_css = _gradient_to_css(grad)
            # Keep bgcolor as fallback for Outlook
            if not bgcolor_attr:
                bgcolor_attr = f' bgcolor="{html.escape(grad.fallback_hex)}"'
            style_parts.append(f"background:{gradient_css}")

        # Resolve effective font for children
        effective_font = parent_font
        if props and props.font_family:
            safe_family = _sanitize_css_value(props.font_family)
            if safe_family:
                effective_font = f"{safe_family},Arial,Helvetica,sans-serif"

        # Build padding string for inner <td> wrapper (NOT <table>).
        # Outlook ignores padding on <table>; only <td> is reliable.
        pad_top = node.padding_top or (props.padding_top if props else 0) or 0
        pad_right = node.padding_right or (props.padding_right if props else 0) or 0
        pad_bottom = node.padding_bottom or (props.padding_bottom if props else 0) or 0
        pad_left = node.padding_left or (props.padding_left if props else 0) or 0
        has_padding = any(v > 0 for v in (pad_top, pad_right, pad_bottom, pad_left))
        padding_css = (
            f"padding:{int(pad_top)}px {int(pad_right)}px {int(pad_bottom)}px {int(pad_left)}px"
            if has_padding
            else ""
        )

        # Nesting depth guard — flatten beyond depth 6
        if _depth > 6:
            logger.warning(
                "design_sync.nesting_depth_exceeded",
                node_id=node.id,
                node_name=node.name,
                depth=_depth,
            )
            flat_lines: list[str] = []
            for child in node.children:
                child_html = node_to_email_html(
                    child,
                    indent=indent + 1,
                    props_map=props_map,
                    parent_bg=effective_bg,
                    parent_font=effective_font,
                    section_map=section_map,
                    button_ids=button_ids,
                    text_meta=text_meta,
                    current_section=section,
                    body_font_size=body_font_size,
                    compat=compat,
                    gradients_map=gradients_map,
                    _depth=_depth + 1,
                    container_width=container_width,
                    slot_counter=slot_counter,
                )
                if child.type != DesignNodeType.TEXT:
                    flat_lines.append(f"{pad}<tr><td>{child_html}</td></tr>")
                else:
                    flat_lines.append(f"{pad}<tr>{child_html}</tr>")
            return "\n".join(flat_lines) if flat_lines else ""

        style_attr = f' style="{";".join(style_parts)}"'
        component_attr = ""
        if _depth == 0 and slot_counter is not None:
            component_attr = f' data-component-name="{html.escape(node.name or "")}"'
        lines = [
            f"{pad}<table{width_attr}{bgcolor_attr}{component_attr}{style_attr}"
            f' cellpadding="0" cellspacing="0" border="0" role="presentation">'
        ]

        if not node.children:
            if has_padding:
                lines.append(f'{pad}  <tr><td style="{padding_css}">&nbsp;</td></tr>')
            else:
                lines.append(f"{pad}  <tr><td>&nbsp;</td></tr>")
        else:
            # Determine layout strategy
            layout_dir = props.layout_direction if props else None
            # DesignNode takes priority
            if node.layout_mode == "HORIZONTAL":
                layout_dir = "row"
            elif node.layout_mode == "VERTICAL":
                layout_dir = "column"

            gap = (props.item_spacing if props else 0) or (node.item_spacing or 0)
            cross_gap = (props.counter_axis_spacing if props else 0) or (
                node.counter_axis_spacing or 0
            )

            if layout_dir == "row":
                # HORIZONTAL: all children in a single <tr>
                rows = [node.children] if node.children else []
            elif layout_dir == "column":
                # VERTICAL: each child in its own <tr>
                rows = [[child] for child in node.children]
            else:
                # No auto-layout: fall back to y-position grouping
                rows = _group_into_rows(node.children, parent_width=node.width)

            # Wrap all rows in a padding <td> if the node has padding
            if has_padding:
                lines.append(f'{pad}  <tr><td style="{padding_css}">')
                lines.append(
                    f'{pad}    <table width="100%" cellpadding="0" cellspacing="0"'
                    f' border="0" role="presentation"'
                    f' style="border-collapse:collapse;'
                    f'mso-table-lspace:0pt;mso-table-rspace:0pt;">'
                )

            gap_px = int(gap)
            effective_width = int(node.width) if node.width else container_width

            for row_idx, row in enumerate(rows):
                # Insert vertical spacer between rows (not before first)
                if row_idx > 0 and gap > 0 and layout_dir in ("column", None):
                    lines.append(
                        f'{pad}    <tr><td style="height:{gap_px}px;'
                        f"font-size:1px;line-height:1px;"
                        f'mso-line-height-rule:exactly;" '
                        f'aria-hidden="true">&nbsp;</td></tr>'
                    )

                # Multi-column row: use hybrid inline-block + MSO ghost table
                if len(row) > 1:
                    col_widths = _calculate_column_widths(
                        row,
                        effective_width,
                        gap=gap_px,
                    )
                    mc_indent = indent + (2 if has_padding else 1)
                    mc_lines = _render_multi_column_row(
                        row,
                        column_widths=col_widths,
                        gap=gap_px,
                        indent=mc_indent,
                        props_map=props_map,
                        parent_bg=effective_bg,
                        parent_font=effective_font,
                        section_map=section_map,
                        button_ids=button_ids,
                        text_meta=text_meta,
                        current_section=section,
                        body_font_size=body_font_size,
                        compat=compat,
                        gradients_map=gradients_map,
                        _depth=_depth,
                        container_width=effective_width,
                        slot_counter=slot_counter,
                    )
                    lines.extend(mc_lines)
                    continue

                # Single-column row: existing rendering
                lines.append(f"{pad}    <tr>")
                for cell_idx, child in enumerate(row):
                    child_html = node_to_email_html(
                        child,
                        indent=indent + (4 if has_padding else 2),
                        props_map=props_map,
                        parent_bg=effective_bg,
                        parent_font=effective_font,
                        section_map=section_map,
                        button_ids=button_ids,
                        text_meta=text_meta,
                        current_section=section,
                        body_font_size=body_font_size,
                        compat=compat,
                        gradients_map=gradients_map,
                        _depth=_depth + 1,
                        container_width=container_width,
                        slot_counter=slot_counter,
                    )

                    if child.type != DesignNodeType.TEXT:
                        # Build <td> style
                        td_styles: list[str] = []
                        if effective_font:
                            td_styles.append(f"font-family:{effective_font}")
                        # Horizontal gap: padding-left on all cells except first
                        if layout_dir == "row" and cell_idx > 0 and gap > 0:
                            td_styles.append(f"padding-left:{int(gap)}px")
                        # Cross-axis padding
                        if cross_gap > 0:
                            if layout_dir == "row":
                                td_styles.append(f"padding-top:{int(cross_gap)}px")
                            elif layout_dir == "column":
                                td_styles.append(f"padding-left:{int(cross_gap)}px")
                        td_style = f' style="{";".join(td_styles)}"' if td_styles else ""
                        lines.append(f"{pad}      <td{td_style}>")
                        lines.append(child_html)
                        lines.append(f"{pad}      </td>")
                    else:
                        lines.append(child_html)
                lines.append(f"{pad}    </tr>")

            if has_padding:
                lines.append(f"{pad}    </table>")
                lines.append(f"{pad}  </td></tr>")
        lines.append(f"{pad}</table>")
        return "\n".join(lines)

    # Vector/other → skip (vectors/SVGs are not email-safe)
    return ""


_LAYOUT_CSS_RE = re.compile(
    r"(?:^|;)\s*(?:width|max-width|float|display\s*:\s*(?:inline-block|flex|grid))",
    re.IGNORECASE,
)

_DIV_TOKEN_RE = re.compile(r"(<div(?:\s[^>]*)?>|</div>)", re.IGNORECASE)
_TD_TAG_RE = re.compile(r"</?td[\s>]", re.IGNORECASE)


def _is_inside_td(html_str: str, pos: int) -> bool:
    """Check whether *pos* is inside a ``<td>`` cell (handles nested tables)."""
    depth = 0
    for m in _TD_TAG_RE.finditer(html_str, 0, pos):
        if m.group().startswith("</"):
            depth -= 1
        else:
            depth += 1
    return depth > 0


def sanitize_web_tags_for_email(html_str: str) -> str:
    """Clean web tags for email-safe output.

    Rules:
    - MSO conditional comments: preserved untouched.
    - ``<p>`` inside ``<td>``: preserved with ``margin:0 0 10px 0`` reset.
    - ``<p>`` outside ``<td>``: stripped → content<br><br> (last gets no trailing <br>).
    - ``<div>`` with layout CSS (width/max-width/flex/float/inline-block):
      converted to ``<table role="presentation"><tr><td>`` wrapper.
    - ``<div>`` simple wrapper inside ``<td>`` (e.g. text-align): preserved.
    - ``<div>`` outside ``<td>`` with no layout CSS: unwrapped.
    """
    # 1. Stash MSO conditionals
    mso_blocks: list[str] = []

    def _stash(m: re.Match[str]) -> str:
        mso_blocks.append(m.group(0))
        return f"__MSO_{len(mso_blocks) - 1}__"

    html_str = re.compile(r"<!--\[if\s[^\]]*\]>.*?<!\[endif\]-->", re.DOTALL).sub(_stash, html_str)

    # 2. Handle <p> tags — preserve inside <td>, strip outside
    p_re = re.compile(r"<p(\s[^>]*)?>(.+?)</p>", re.DOTALL)
    matches = list(p_re.finditer(html_str))
    for i, m in enumerate(reversed(matches)):
        idx_from_end = i  # 0 = last match
        if _is_inside_td(html_str, m.start()):
            attrs = m.group(1) or ""
            if "margin" not in attrs:
                if "style=" in attrs:
                    attrs = attrs.replace('style="', 'style="margin:0 0 10px 0;')
                    attrs = attrs.replace("style='", "style='margin:0 0 10px 0;")
                else:
                    attrs = ' style="margin:0 0 10px 0;"'
            replacement = f"<p{attrs}>{m.group(2)}</p>"
            html_str = html_str[: m.start()] + replacement + html_str[m.end() :]
        else:
            suffix = "" if idx_from_end == 0 else "<br><br>"
            html_str = html_str[: m.start()] + m.group(2) + suffix + html_str[m.end() :]

    # 3. Handle <div>...</div> pairs with a stack-based approach
    tokens = list(_DIV_TOKEN_RE.finditer(html_str))

    # Pair open/close tags via stack, classify + extract style in one pass
    pairs: list[tuple[str, str, int, int]] = []  # (action, style_val, open_idx, close_idx)
    stack: list[int] = []
    for ti, tok in enumerate(tokens):
        if tok.group().startswith("</"):
            if stack:
                open_idx = stack.pop()
                open_tok = tokens[open_idx]
                attrs_match = re.match(r"<div(\s[^>]*)?>", open_tok.group(), re.IGNORECASE)
                attrs = attrs_match.group(1) if attrs_match and attrs_match.group(1) else ""
                style_match = re.search(r'style=["\']([^"\']*)["\']', attrs)
                style_val = style_match.group(1) if style_match else ""

                if _LAYOUT_CSS_RE.search(style_val):
                    action = "convert"
                elif _is_inside_td(html_str, open_tok.start()):
                    action = "preserve"
                else:
                    action = "unwrap"
                pairs.append((action, style_val, open_idx, ti))
        else:
            stack.append(ti)

    # Build replacements from classified pairs
    all_replacements: list[tuple[int, int, str]] = []
    for action, style_val, open_idx, close_idx in pairs:
        open_tok = tokens[open_idx]
        close_tok = tokens[close_idx]

        if action == "convert":
            # Sanitize to prevent attribute breakout (defense-in-depth)
            safe_style = (
                style_val.replace('"', "").replace("'", "").replace("<", "").replace(">", "")
            )
            table_open = (
                '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
                f'<tr><td style="{safe_style}">'
            )
            all_replacements.append((open_tok.start(), open_tok.end(), table_open))
            all_replacements.append((close_tok.start(), close_tok.end(), "</td></tr></table>"))
        elif action == "preserve":
            pass  # keep both open and close as-is
        else:  # unwrap
            all_replacements.append((open_tok.start(), open_tok.end(), ""))
            all_replacements.append((close_tok.start(), close_tok.end(), ""))

    # Apply replacements in reverse order
    for start, end, replacement in sorted(all_replacements, key=lambda r: r[0], reverse=True):
        html_str = html_str[:start] + replacement + html_str[end:]

    # 4. Restore MSO blocks
    for i, block in enumerate(mso_blocks):
        html_str = html_str.replace(f"__MSO_{i}__", block)

    return html_str


def _group_into_rows(
    nodes: list[DesignNode],
    tolerance: float = 20.0,
    *,
    parent_width: float | None = None,
) -> list[list[DesignNode]]:
    """Group sibling nodes into rows based on y-position proximity.

    Handles three cases for y-position data:
    - All y=None: treat as single horizontal row (auto-layout without positions).
    - All y known: sort+group by y-position proximity (tolerance default 20px).
    - Mixed: group y-known nodes normally, append y=None nodes to last row.

    Hero image detection: a single IMAGE node spanning >=80% of
    the parent width gets its own row regardless of y-tolerance.
    """
    if not nodes:
        return []

    # Partition into y-known and y-unknown
    y_known = [n for n in nodes if n.y is not None]
    y_unknown = [n for n in nodes if n.y is None]

    # All y=None → single horizontal row (auto-layout assumption)
    if not y_known:
        return [nodes]

    sorted_nodes = sorted(y_known, key=lambda n: (n.y or 0, n.x or 0))
    rows: list[list[DesignNode]] = [[sorted_nodes[0]]]

    for node in sorted_nodes[1:]:
        last_row_y = rows[-1][0].y or 0
        node_y = node.y or 0
        if abs(node_y - last_row_y) <= tolerance:
            rows[-1].append(node)
        else:
            rows.append([node])

    # Mixed: append y-unknown nodes to the last row
    if y_unknown:
        rows[-1].extend(y_unknown)

    # Sort each row by x-position (left to right)
    for row in rows:
        row.sort(key=lambda n: n.x or 0)

    # Hero image detection: split wide images into their own rows
    if parent_width and parent_width > 0:
        threshold = parent_width * 0.8
        final_rows: list[list[DesignNode]] = []
        for row in rows:
            hero_nodes: list[DesignNode] = []
            other_nodes: list[DesignNode] = []
            for n in row:
                if (
                    n.type == DesignNodeType.IMAGE
                    and n.width is not None
                    and n.width >= threshold
                    and len(row) > 1
                ):
                    hero_nodes.append(n)
                else:
                    other_nodes.append(n)
            for hero in hero_nodes:
                final_rows.append([hero])
            if other_nodes:
                final_rows.append(other_nodes)
        rows = final_rows

    return rows


def _calculate_column_widths(
    children: list[DesignNode],
    container_width: float,
    gap: float = 0,
) -> list[int]:
    """Calculate proportional pixel widths for multi-column children.

    Args:
        children: Column child nodes (must have len >= 1).
        container_width: Available parent width in pixels.
        gap: Gap between columns in pixels.

    Returns:
        List of integer pixel widths, one per child. Last column absorbs rounding.
    """
    n = len(children)
    if n == 0:
        return []
    if n == 1:
        return [int(container_width)]

    total_gap = gap * (n - 1)
    avail = max(container_width - total_gap, n)  # at least 1px per column

    known = [(i, c.width) for i, c in enumerate(children) if c.width is not None]
    unknown_indices = [i for i, c in enumerate(children) if c.width is None]

    widths = [0] * n

    if len(known) == n:
        # All children have widths — proportional distribution
        total_child_w = sum(w for _, w in known)
        if total_child_w > 0:
            for i, w in known:
                widths[i] = round(avail * (w / total_child_w))
        else:
            per = int(avail / n)
            widths = [per] * n
    elif not known:
        # No children have widths — equal distribution
        per = int(avail / n)
        widths = [per] * n
    else:
        # Mixed: proportional for known, split remainder for unknown
        total_known_w = sum(w for _, w in known)
        if total_known_w > 0:
            for i, w in known:
                widths[i] = round(avail * (w / total_known_w) * (len(known) / n))
        used = sum(widths[i] for i, _ in known)
        remainder = int(avail) - used
        if unknown_indices:
            per_unknown = remainder // len(unknown_indices)
            for i in unknown_indices:
                widths[i] = per_unknown

    # Last column absorbs rounding error
    widths[-1] = int(avail) - sum(widths[:-1])

    return widths


def _render_multi_column_row(
    children: list[DesignNode],
    *,
    column_widths: list[int],
    gap: int,
    indent: int,
    props_map: dict[str, _NodeProps] | None,
    parent_bg: str | None,
    parent_font: str | None,
    section_map: dict[str, EmailSection] | None,
    button_ids: set[str] | None,
    text_meta: dict[str, TextBlock] | None,
    current_section: EmailSection | None,
    body_font_size: float,
    compat: ConverterCompatibility | None,
    gradients_map: dict[str, ExtractedGradient] | None,
    _depth: int,
    container_width: int,
    slot_counter: dict[str, int] | None = None,
) -> list[str]:
    """Render a multi-column row using hybrid inline-block + MSO ghost table.

    Returns a list of HTML lines forming a single ``<tr>`` with columns rendered
    as ``display:inline-block`` divs for modern clients and an MSO ghost table
    for Outlook.
    """
    pad = "  " * indent
    inner_pad = "  " * (indent + 1)
    col_pad = "  " * (indent + 2)
    lines: list[str] = []

    # Compatibility warning for display:inline-block (once per row)
    if compat:
        compat.check_and_warn(
            "display",
            value="inline-block",
            context="Multi-column layout",
        )

    # Open outer <tr><td>
    lines.append(f"{pad}<tr>")
    lines.append(
        f'{inner_pad}<td style="font-size:0;text-align:center;mso-line-height-rule:exactly;">'
    )

    # Open MSO ghost table
    lines.append(
        f"{inner_pad}<!--[if mso]>"
        f'<table role="presentation" width="{container_width}"'
        f' cellpadding="0" cellspacing="0" border="0"'
        f' style="border-collapse:collapse;mso-table-lspace:0pt;'
        f'mso-table-rspace:0pt;">'
        f"<tr><![endif]-->"
    )

    for col_idx, (child, col_width) in enumerate(zip(children, column_widths, strict=True)):
        # MSO spacer between columns
        if col_idx > 0 and gap > 0:
            lines.append(f'{inner_pad}<!--[if mso]><td width="{gap}"></td><![endif]-->')

        # MSO column open
        lines.append(f'{inner_pad}<!--[if mso]><td width="{col_width}" valign="top"><![endif]-->')

        # Modern wrapper div
        lines.append(
            f'{inner_pad}<div class="column" style="display:inline-block;'
            f"max-width:{col_width}px;width:100%;vertical-align:top;"
            f'">'
        )

        # Inner table
        lines.append(
            f'{col_pad}<table role="presentation" width="100%"'
            f' cellpadding="0" cellspacing="0" border="0"'
            f' style="border-collapse:collapse;mso-table-lspace:0pt;'
            f'mso-table-rspace:0pt;">'
        )

        # Recurse into child
        child_html = node_to_email_html(
            child,
            indent=indent + 3,
            props_map=props_map,
            parent_bg=parent_bg,
            parent_font=parent_font,
            section_map=section_map,
            button_ids=button_ids,
            text_meta=text_meta,
            current_section=current_section,
            body_font_size=body_font_size,
            compat=compat,
            gradients_map=gradients_map,
            _depth=_depth + 1,
            container_width=col_width,
            slot_counter=slot_counter,
        )

        if child.type == DesignNodeType.TEXT:
            lines.append(f"{col_pad}  <tr>{child_html}</tr>")
        else:
            lines.append(f"{col_pad}  <tr><td>{child_html}</td></tr>")

        # Close inner table + div
        lines.append(f"{col_pad}</table>")
        lines.append(f"{inner_pad}</div>")

        # MSO column close
        lines.append(f"{inner_pad}<!--[if mso]></td><![endif]-->")

    # Close MSO ghost table
    lines.append(f"{inner_pad}<!--[if mso]></tr></table><![endif]-->")

    # Close outer </td></tr>
    lines.append(f"{inner_pad}</td>")
    lines.append(f"{pad}</tr>")

    return lines
