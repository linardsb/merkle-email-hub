"""Feature detection HTML templates for CSS property change detection."""

from __future__ import annotations

from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent

# Map: template filename (without .html) → ontology property_id
FEATURE_TEMPLATES: dict[str, str] = {
    "flexbox_display-flex": "display-flex",
    "flexbox_gap": "gap",
    "grid_display-grid": "display-grid",
    "grid_grid-template-columns": "grid-template-columns",
    "custom-properties_var": "css-variables",
    "layout_aspect-ratio": "aspect-ratio",
    "layout_clamp": "clamp",
    "layout_object-fit": "object-fit",
    "layout_position-sticky": "position-sticky",
    "box-model_max-width": "max-width",
    "box-model_margin-inline": "margin-inline",
    "box-model_padding-block": "padding-block",
    "typography_font-display": "font-display",
    "typography_text-decoration-color": "text-decoration-color",
    "color_currentcolor": "currentcolor",
    "color_opacity": "opacity",
    "color_hsl": "hsl",
    "border_border-radius": "border-radius",
    "border_box-shadow": "box-shadow",
    "selector_has": "has-selector",
    "selector_is": "is-selector",
    "media_prefers-color-scheme": "prefers-color-scheme",
    "media_prefers-reduced-motion": "prefers-reduced-motion",
    "dark-mode_color-scheme": "color-scheme",
    "transform_transform": "transform",
}


def get_template_html(template_name: str) -> str:
    """Load a feature detection template by name."""
    path = _TEMPLATE_DIR / f"{template_name}.html"
    return path.read_text(encoding="utf-8")


def list_templates() -> list[str]:
    """List all available template names."""
    return sorted(FEATURE_TEMPLATES.keys())
