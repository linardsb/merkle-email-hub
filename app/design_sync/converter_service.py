"""Service layer for design-to-email HTML conversion (provider-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.design_sync.converter import (
    _NodeProps,
    _sanitize_css_value,
    convert_colors_to_palette,
    convert_typography,
    node_to_email_html,
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
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" width="600" style="margin:0 auto;max-width:600px;width:100%;" cellpadding="0" cellspacing="0" border="0">
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

        # Collect top-level frames from all pages
        frames = self._collect_frames(structure, selected_nodes)

        if not frames:
            logger.warning("design_sync.converter_no_frames")
            return ConversionResult(html="", sections_count=0, warnings=["No frames found"])

        # Build props_map: from raw file data (Penpot) or from DesignNode tree (Figma)
        if raw_file_data:
            props_map = self._build_props_map(raw_file_data)
        else:
            props_map = self._build_props_map_from_nodes(frames)

        # Convert each frame to HTML section
        section_parts: list[str] = []
        for frame in frames:
            # Check for VECTOR nodes that will be stripped
            self._collect_vector_warnings(frame, warnings)
            section_html = node_to_email_html(frame, indent=1, props_map=props_map or None)
            section_parts.append(f"<tr><td>\n{section_html}\n</td></tr>")

        sections_html = "\n".join(section_parts)

        # Apply token-derived values (sanitize for CSS context)
        palette = convert_colors_to_palette(tokens.colors)
        bg_color = _sanitize_css_value(palette.background) or "#ffffff"
        text_color = _sanitize_css_value(palette.text) or "#000000"

        typography = convert_typography(tokens.typography)
        safe_body_font = _sanitize_css_value(typography.body_font)
        style_block = f"<style>body {{ font-family: {safe_body_font}; }}</style>"

        result_html = EMAIL_SKELETON.format(
            style_block=style_block,
            bg_color=bg_color,
            text_color=text_color,
            body_font=safe_body_font or "Arial, Helvetica, sans-serif",
            sections=sections_html,
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
        """Build props_map from DesignNode fill_color fields (provider-agnostic)."""
        props: dict[str, _NodeProps] = {}

        def _walk(node: DesignNode) -> None:
            if node.fill_color:
                props[node.id] = _NodeProps(bg_color=node.fill_color)
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
