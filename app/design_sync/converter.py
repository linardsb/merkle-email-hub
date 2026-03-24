"""Convert design elements to email-safe HTML and design system tokens (provider-agnostic)."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from app.core.logging import get_logger
from app.design_sync.protocol import (
    DesignNode,
    DesignNodeType,
    ExtractedColor,
    ExtractedTypography,
)
from app.projects.design_system import BrandPalette, Typography

logger = get_logger(__name__)

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

    def _font_stack(family: str) -> str:
        """Build email-safe CSS font stack."""
        safe_fallbacks = {
            "sans-serif": "Arial, Helvetica, sans-serif",
            "serif": "Georgia, Times New Roman, serif",
            "monospace": "Courier New, monospace",
        }
        family_clean = family.strip("'\"")
        if "," in family_clean:
            return family_clean
        for generic, fallback in safe_fallbacks.items():
            if generic in family_clean.lower():
                return fallback
        return f"{family_clean}, Arial, Helvetica, sans-serif"

    return Typography(
        heading_font=_font_stack(heading_style.family),
        body_font=_font_stack(body_style.family),
        base_size=f"{int(body_style.size)}px",
    )


def _contrasting_text_color(bg_hex: str) -> str:
    """Return white or black text depending on background luminance."""
    return "#ffffff" if _relative_luminance(bg_hex) < 0.5 else "#000000"


def node_to_email_html(
    node: DesignNode,
    *,
    indent: int = 0,
    props_map: dict[str, _NodeProps] | None = None,
    parent_bg: str | None = None,
    parent_font: str | None = None,
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
    """
    pad = "  " * indent
    props = props_map.get(node.id) if props_map else None

    if node.type == DesignNodeType.TEXT:
        content = html.escape(node.text_content or "")
        font_family = parent_font or "Arial,Helvetica,sans-serif"
        extra_style = ""
        if props:
            if props.font_family:
                # Sanitize: strip anything that could break out of a CSS value
                safe_family = _sanitize_css_value(props.font_family)
                if safe_family:
                    font_family = f"{safe_family},Arial,Helvetica,sans-serif"
            if props.font_size:
                extra_style += f"font-size:{int(props.font_size)}px;"
            if props.font_weight:
                safe_weight = _sanitize_css_value(props.font_weight)
                if safe_weight:
                    extra_style += f"font-weight:{safe_weight};"
        # Color priority: node.text_color (from design) > contrast auto > none
        if node.text_color:
            safe_text_color = _sanitize_css_value(node.text_color)
            if safe_text_color:
                extra_style += f"color:{safe_text_color};"
        elif parent_bg:
            extra_style += f"color:{_contrasting_text_color(parent_bg)};"
        return f'{pad}<td style="font-family:{font_family};{extra_style}">{content}</td>'

    if node.type == DesignNodeType.IMAGE:
        w = f' width="{int(node.width)}"' if node.width else ""
        h = f' height="{int(node.height)}"' if node.height else ""
        alt = html.escape(node.name or "")
        node_id_attr = f' data-node-id="{html.escape(node.id)}"'
        return (
            f'{pad}<img src="" alt="{alt}"{node_id_attr}{w}{h}'
            f' style="display:block;border:0;width:100%;height:auto;" />'
        )

    # Frame/Group/Component/Instance → table with rows
    if node.type in (
        DesignNodeType.FRAME,
        DesignNodeType.GROUP,
        DesignNodeType.COMPONENT,
        DesignNodeType.INSTANCE,
    ):
        # Nested frames use 100% to fill parent; the converter_service wraps
        # top-level frames in <tr><td>, so 100% is correct at every level.
        width_attr = ' width="100%"'
        bgcolor_attr = ""
        style_parts: list[str] = []
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

        # Resolve effective font for children
        effective_font = parent_font
        if props and props.font_family:
            safe_family = _sanitize_css_value(props.font_family)
            if safe_family:
                effective_font = f"{safe_family},Arial,Helvetica,sans-serif"

        if props:
            pad_vals = [
                props.padding_top,
                props.padding_right,
                props.padding_bottom,
                props.padding_left,
            ]
            if any(v > 0 for v in pad_vals):
                style_parts.append(
                    f"padding:{int(props.padding_top)}px {int(props.padding_right)}px "
                    f"{int(props.padding_bottom)}px {int(props.padding_left)}px"
                )

        style_attr = f' style="{";".join(style_parts)}"' if style_parts else ""
        lines = [
            f"{pad}<table{width_attr}{bgcolor_attr}{style_attr}"
            f' cellpadding="0" cellspacing="0" border="0" role="presentation">'
        ]

        if not node.children:
            lines.append(f"{pad}  <tr><td>&nbsp;</td></tr>")
        else:
            rows = _group_into_rows(node.children, parent_width=node.width)
            for row in rows:
                lines.append(f"{pad}  <tr>")
                for child in row:
                    child_html = node_to_email_html(
                        child,
                        indent=indent + 2,
                        props_map=props_map,
                        parent_bg=effective_bg,
                        parent_font=effective_font,
                    )
                    if child.type != DesignNodeType.TEXT:
                        font_style = (
                            f' style="font-family:{effective_font};"' if effective_font else ""
                        )
                        lines.append(f"{pad}    <td{font_style}>")
                        lines.append(child_html)
                        lines.append(f"{pad}    </td>")
                    else:
                        lines.append(child_html)
                lines.append(f"{pad}  </tr>")
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
    tolerance: float = 10.0,
    *,
    parent_width: float | None = None,
) -> list[list[DesignNode]]:
    """Group sibling nodes into rows based on y-position proximity.

    Hero image detection: a single IMAGE node spanning >=80% of
    the parent width gets its own row regardless of y-tolerance.
    """
    if not nodes:
        return []

    sorted_nodes = sorted(nodes, key=lambda n: (n.y or 0, n.x or 0))
    rows: list[list[DesignNode]] = [[sorted_nodes[0]]]

    for node in sorted_nodes[1:]:
        last_row_y = rows[-1][0].y or 0
        node_y = node.y or 0
        if abs(node_y - last_row_y) <= tolerance:
            rows[-1].append(node)
        else:
            rows.append([node])

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
