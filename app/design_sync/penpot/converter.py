"""Backward-compatible re-export — converter moved to app.design_sync.converter."""

from app.design_sync.converter import (
    _NODE_HTML_MAP,
    _contrasting_text_color,
    _group_into_rows,
    _NodeProps,
    _relative_luminance,
    _sanitize_css_value,
    convert_colors_to_palette,
    convert_typography,
    node_to_email_html,
)

__all__ = [
    "_NODE_HTML_MAP",
    "_NodeProps",
    "_contrasting_text_color",
    "_group_into_rows",
    "_relative_luminance",
    "_sanitize_css_value",
    "convert_colors_to_palette",
    "convert_typography",
    "node_to_email_html",
]
