"""Service layer for design-to-email HTML conversion (provider-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.design_sync.compatibility import CompatibilityHint, ConverterCompatibility
from app.design_sync.converter import (
    _NodeProps,
    _sanitize_css_value,
    convert_colors_to_palette,
    convert_typography,
    node_to_email_html,
)
from app.design_sync.figma.layout_analyzer import (
    DesignLayoutDescription,
    EmailSection,
    TextBlock,
    analyze_layout,
)
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExtractedTokens,
)

logger = get_logger(__name__)


EMAIL_SKELETON = """<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="format-detection" content="telephone=no,date=no,address=no,email=no,url=no">
<meta name="x-apple-disable-message-reformatting">
<!--[if mso]>
<noscript><xml>
<o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml></noscript>
<![endif]-->
{style_block}
</head>
<body role="article" aria-roledescription="email" lang="en" style="margin:0;padding:0;word-spacing:normal;background-color:{bg_color};color:{text_color};font-family:{body_font};text-size-adjust:100%;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
<!--[if mso]>
<table role="presentation" width="{container_width}" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;"><tr><td>
<![endif]-->
<table role="presentation" width="{container_width}" style="margin:0 auto;max-width:{container_width}px;width:100%;border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;" cellpadding="0" cellspacing="0" border="0">
{sections}
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->
</body>
</html>"""


@dataclass(frozen=True)
class ConversionResult:
    """Result of converting a design tree to email HTML."""

    html: str
    sections_count: int
    warnings: list[str] = field(default_factory=list)
    layout: DesignLayoutDescription | None = None
    compatibility_hints: list[CompatibilityHint] = field(default_factory=list)


# Backward-compatible alias
PenpotConversionResult = ConversionResult


class DesignConverterService:
    """Orchestrates design tree → email HTML conversion (provider-agnostic)."""

    def convert(
        self,
        structure: DesignFileStructure,
        tokens: ExtractedTokens,
        *,
        raw_file_data: dict[str, Any] | None = None,
        selected_nodes: list[str] | None = None,
        target_clients: list[str] | None = None,
    ) -> ConversionResult:
        """Convert a design file structure into an email HTML skeleton.

        Args:
            structure: Parsed design file structure with pages and nodes.
            tokens: Extracted design tokens (colors, typography, spacing).
            raw_file_data: Raw file data for supplementary properties (Penpot only).
            selected_nodes: If provided, only convert frames with these IDs.

        Returns:
            ConversionResult with HTML skeleton and metadata.
        """
        warnings: list[str] = []
        compat = ConverterCompatibility(target_clients=target_clients)

        # Collect top-level frames from all pages
        frames = self._collect_frames(structure, selected_nodes)

        if not frames:
            logger.warning("design_sync.converter_no_frames")
            return ConversionResult(html="", sections_count=0, warnings=["No frames found"])

        # Run layout analysis on full structure
        layout = analyze_layout(structure)

        # Build O(1) lookup maps from layout analysis
        sections_by_node_id: dict[str, EmailSection] = {
            section.node_id: section for section in layout.sections
        }

        button_node_ids: set[str] = set()
        for section in layout.sections:
            for btn in section.buttons:
                button_node_ids.add(btn.node_id)

        text_meta: dict[str, TextBlock] = {}
        for section in layout.sections:
            for tb in section.texts:
                text_meta[tb.node_id] = tb

        # Derive container width (clamped 400-800)
        container_width = 600
        if layout.overall_width is not None:
            container_width = max(400, min(800, int(layout.overall_width)))

        # Build props_map: from raw file data (Penpot) or from DesignNode tree (Figma)
        if raw_file_data:
            props_map = self._build_props_map(raw_file_data)
        else:
            props_map = self._build_props_map_from_nodes(frames)

        # Compute body font size from typography tokens for heading detection
        typography = convert_typography(tokens.typography)
        body_font_size = 16.0
        if typography.base_size:
            try:
                body_font_size = float(typography.base_size.replace("px", ""))
            except (ValueError, TypeError):
                pass

        # Convert each frame to HTML section
        section_parts: list[str] = []
        for frame in frames:
            self._collect_vector_warnings(frame, warnings)
            section_html = node_to_email_html(
                frame,
                indent=1,
                props_map=props_map or None,
                section_map=sections_by_node_id,
                button_ids=button_node_ids,
                text_meta=text_meta,
                body_font_size=body_font_size,
                compat=compat,
            )
            section_parts.append(f"<tr><td>\n{section_html}\n</td></tr>")

            # Inter-section spacer from layout analysis
            frame_section = sections_by_node_id.get(frame.id)
            if frame_section and frame_section.spacing_after and frame_section.spacing_after > 0:
                spacer_h = int(frame_section.spacing_after)
                section_parts.append(
                    f'<tr><td style="height:{spacer_h}px;font-size:1px;'
                    f'line-height:1px;mso-line-height-rule:exactly;" '
                    f'aria-hidden="true">&nbsp;</td></tr>'
                )

        sections_html = "\n".join(section_parts)

        # Apply token-derived values (sanitize for CSS context)
        palette = convert_colors_to_palette(tokens.colors)
        bg_color = _sanitize_css_value(palette.background) or "#ffffff"
        text_color = _sanitize_css_value(palette.text) or "#000000"

        safe_body_font = _sanitize_css_value(typography.body_font)
        style_block = (
            "<style>\n"
            f"  body {{ font-family: {safe_body_font}; margin: 0; padding: 0; }}\n"
            "  table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }\n"
            "  img { -ms-interpolation-mode: bicubic; border: 0; display: block;"
            " outline: none; text-decoration: none; }\n"
            "</style>"
        )

        # Check max-width support (used on wrapper table)
        if compat.has_targets:
            compat.check_and_warn("max-width", context="Email wrapper table")

        result_html = EMAIL_SKELETON.format(
            style_block=style_block,
            bg_color=bg_color,
            text_color=text_color,
            body_font=safe_body_font or "Arial, Helvetica, sans-serif",
            sections=sections_html,
            container_width=container_width,
        )

        logger.info(
            "design_sync.converter_result",
            sections_count=len(frames),
            warnings_count=len(warnings),
        )

        return ConversionResult(
            html=result_html,
            sections_count=len(frames),
            warnings=warnings,
            layout=layout,
            compatibility_hints=compat.hints,
        )

    def _collect_frames(
        self,
        structure: DesignFileStructure,
        selected_nodes: list[str] | None,
    ) -> list[DesignNode]:
        """Walk pages and collect top-level FRAME/COMPONENT/INSTANCE nodes."""
        frames: list[DesignNode] = []
        frame_types = {DesignNodeType.FRAME, DesignNodeType.COMPONENT, DesignNodeType.INSTANCE}

        for page in structure.pages:
            for child in page.children:
                if child.type in frame_types:
                    if selected_nodes is None or child.id in selected_nodes:
                        frames.append(child)
        return frames

    def _collect_vector_warnings(self, node: DesignNode, warnings: list[str]) -> None:
        """Recursively collect warnings for VECTOR nodes that will be stripped."""
        if node.type == DesignNodeType.VECTOR:
            warnings.append(
                f"SVG/vector node '{node.name}' (id={node.id}) stripped — not email-safe"
            )
        for child in node.children:
            self._collect_vector_warnings(child, warnings)

    def _build_props_map_from_nodes(self, frames: list[DesignNode]) -> dict[str, _NodeProps]:
        """Build props_map from DesignNode fields (provider-agnostic)."""
        props: dict[str, _NodeProps] = {}

        def _walk(node: DesignNode) -> None:
            has_data = bool(
                node.fill_color
                or node.font_family
                or node.font_size
                or node.font_weight
                or node.padding_top
                or node.padding_right
                or node.padding_bottom
                or node.padding_left
                or node.layout_mode
                or node.item_spacing
                or node.counter_axis_spacing
                or node.line_height_px
                or node.letter_spacing_px
                or node.text_transform
                or node.text_decoration
            )
            if has_data:
                props[node.id] = _NodeProps(
                    bg_color=node.fill_color,
                    font_family=node.font_family,
                    font_size=node.font_size,
                    font_weight=str(node.font_weight) if node.font_weight else None,
                    padding_top=node.padding_top or 0,
                    padding_right=node.padding_right or 0,
                    padding_bottom=node.padding_bottom or 0,
                    padding_left=node.padding_left or 0,
                    layout_direction=(
                        "row"
                        if node.layout_mode == "HORIZONTAL"
                        else "column"
                        if node.layout_mode == "VERTICAL"
                        else None
                    ),
                    item_spacing=node.item_spacing or 0,
                    counter_axis_spacing=node.counter_axis_spacing or 0,
                    line_height_px=node.line_height_px,
                    letter_spacing_px=node.letter_spacing_px,
                    text_transform=node.text_transform,
                    text_decoration=node.text_decoration,
                )
            for child in node.children:
                _walk(child)

        for frame in frames:
            _walk(frame)
        return props

    def _build_props_map(self, file_data: dict[str, Any]) -> dict[str, _NodeProps]:
        """Extract visual properties from raw Penpot objects."""
        props: dict[str, _NodeProps] = {}
        pages_index = file_data.get("data", {}).get("pages-index", {})
        for _page_id, page_data in pages_index.items():
            if not isinstance(page_data, dict):
                continue
            for obj_id, obj in page_data.get("objects", {}).items():
                if not isinstance(obj, dict):
                    continue
                bg = self._extract_bg(obj)
                font = obj.get("font-family")
                size = obj.get("font-size")
                weight = str(obj.get("font-weight", "")) or None
                padding = obj.get("layout-padding", {})
                if not isinstance(padding, dict):
                    padding = {}
                props[str(obj_id)] = _NodeProps(
                    bg_color=bg,
                    font_family=str(font) if font else None,
                    font_size=float(size) if size else None,
                    font_weight=weight,
                    padding_top=float(padding.get("p1", 0)),
                    padding_right=float(padding.get("p2", 0)),
                    padding_bottom=float(padding.get("p3", 0)),
                    padding_left=float(padding.get("p4", 0)),
                    layout_direction=str(obj.get("layout-flex-dir"))
                    if obj.get("layout-flex-dir")
                    else None,
                    item_spacing=float(obj.get("layout-gap", {}).get("row-gap", 0))
                    if isinstance(obj.get("layout-gap"), dict)
                    else 0,
                    counter_axis_spacing=float(obj.get("layout-gap", {}).get("column-gap", 0))
                    if isinstance(obj.get("layout-gap"), dict)
                    else 0,
                )
        return props

    @staticmethod
    def _extract_bg(obj: dict[str, Any]) -> str | None:
        """Extract first solid fill color from Penpot fills array."""
        fills = obj.get("fills", [])
        if not isinstance(fills, list):
            return None
        for fill in fills:
            if isinstance(fill, dict) and fill.get("fill-color"):
                return str(fill["fill-color"])
        return None


# Backward-compatible alias
PenpotConverterService = DesignConverterService
