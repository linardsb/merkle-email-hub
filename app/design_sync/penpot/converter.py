"""Convert Penpot design elements to email-safe HTML and design system tokens."""

from __future__ import annotations

from app.core.logging import get_logger
from app.design_sync.protocol import (
    DesignNode,
    DesignNodeType,
    ExtractedColor,
    ExtractedTypography,
)
from app.projects.design_system import BrandPalette, Typography

logger = get_logger(__name__)

# Penpot node type → HTML element mapping for email
_NODE_HTML_MAP: dict[DesignNodeType, str] = {
    DesignNodeType.FRAME: "table",
    DesignNodeType.TEXT: "td",
    DesignNodeType.IMAGE: "img",
    DesignNodeType.GROUP: "table",
    DesignNodeType.VECTOR: "div",
}


def convert_colors_to_palette(colors: list[ExtractedColor]) -> BrandPalette:
    """Map extracted Penpot colors to BrandPalette.

    Heuristic: match color names to palette roles (primary, secondary, accent,
    background, text, link). Falls back to positional assignment.
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

    return BrandPalette(
        primary=role_map.get("primary", "#333333"),
        secondary=role_map.get("secondary", "#666666"),
        accent=role_map.get("accent", "#0066cc"),
        background=role_map.get("background", "#ffffff"),
        text=role_map.get("text", "#000000"),
        link=role_map.get("link", "#0000ee"),
    )


def convert_typography(styles: list[ExtractedTypography]) -> Typography:
    """Map extracted Penpot typography to Typography design system model.

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


def node_to_email_html(node: DesignNode, *, indent: int = 0) -> str:
    """Convert a Penpot DesignNode tree to email-safe HTML (table layout).

    Converts flex/grid frames to table rows/cells.
    This produces a structural skeleton — the Scaffolder fills content.
    """
    pad = "  " * indent

    if node.type == DesignNodeType.TEXT:
        content = node.text_content or ""
        return f'{pad}<td style="font-family:Arial,Helvetica,sans-serif;">{content}</td>'

    if node.type == DesignNodeType.IMAGE:
        w = f' width="{int(node.width)}"' if node.width else ""
        h = f' height="{int(node.height)}"' if node.height else ""
        return f'{pad}<img src="" alt=""{w}{h} style="display:block;border:0;" />'

    # Frame/Group → table with rows
    if node.type in (
        DesignNodeType.FRAME,
        DesignNodeType.GROUP,
        DesignNodeType.COMPONENT,
    ):
        width_attr = f' width="{int(node.width)}"' if node.width else ""
        lines = [
            f'{pad}<table{width_attr} cellpadding="0" cellspacing="0" border="0" role="presentation">'
        ]

        if not node.children:
            lines.append(f"{pad}  <tr><td>&nbsp;</td></tr>")
        else:
            rows = _group_into_rows(node.children)
            for row in rows:
                lines.append(f"{pad}  <tr>")
                for child in row:
                    child_html = node_to_email_html(child, indent=indent + 2)
                    if child.type != DesignNodeType.TEXT:
                        lines.append(f"{pad}    <td>")
                        lines.append(child_html)
                        lines.append(f"{pad}    </td>")
                    else:
                        lines.append(child_html)
                lines.append(f"{pad}  </tr>")
        lines.append(f"{pad}</table>")
        return "\n".join(lines)

    # Vector/other → div placeholder
    return f'{pad}<div style="display:block;">&nbsp;</div>'


def _group_into_rows(nodes: list[DesignNode], tolerance: float = 10.0) -> list[list[DesignNode]]:
    """Group sibling nodes into rows based on y-position proximity."""
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

    return rows
