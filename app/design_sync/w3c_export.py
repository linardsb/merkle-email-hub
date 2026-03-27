# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
"""W3C Design Tokens v1.0 JSON exporter.

Converts validated ExtractedTokens back to W3C Design Tokens v1.0 JSON
for downstream tooling (Style Dictionary, Tokens Studio, Figma).
"""

from __future__ import annotations

from typing import Any

from app.design_sync.protocol import ExtractedTokens


def export_w3c_tokens(tokens: ExtractedTokens) -> dict[str, Any]:
    """Convert ExtractedTokens to W3C Design Tokens v1.0 JSON.

    Groups tokens by type following the W3C spec structure.
    Dark colors are emitted via ``$extensions.mode.dark``.
    """
    result: dict[str, Any] = {}

    # Colors
    if tokens.colors:
        color_group: dict[str, Any] = {"$type": "color"}
        for c in tokens.colors:
            color_group[c.name] = {"$value": _w3c_color_value(c.hex, c.opacity)}
        result["color"] = color_group

    # Dark mode colors via $extensions.mode
    if tokens.dark_colors:
        dark_group: dict[str, Any] = {}
        for c in tokens.dark_colors:
            dark_group[c.name] = {
                "$type": "color",
                "$value": _w3c_color_value(c.hex, c.opacity),
            }
        if "color" not in result:
            result["color"] = {"$type": "color"}
        color_group_ref: dict[str, Any] = result["color"]
        color_group_ref["$extensions"] = {"mode": {"dark": dark_group}}

    # Typography — each style becomes a group with fontFamily/fontWeight/fontSize
    if tokens.typography:
        typo_group: dict[str, Any] = {}
        for t in tokens.typography:
            entry: dict[str, Any] = {
                "family": {"$type": "fontFamily", "$value": t.family},
                "weight": {
                    "$type": "fontWeight",
                    "$value": int(t.weight) if t.weight.isdigit() else t.weight,
                },
                "size": {"$type": "fontSize", "$value": f"{t.size}px"},
            }
            if t.line_height:
                entry["lineHeight"] = {
                    "$type": "dimension",
                    "$value": f"{t.line_height}px",
                }
            if t.letter_spacing is not None:
                entry["letterSpacing"] = {
                    "$type": "dimension",
                    "$value": f"{t.letter_spacing}px",
                }
            typo_group[t.name] = entry
        result["typography"] = typo_group

    # Spacing
    if tokens.spacing:
        spacing_group: dict[str, Any] = {"$type": "dimension"}
        for s in tokens.spacing:
            spacing_group[s.name] = {"$value": f"{s.value}px"}
        result["spacing"] = spacing_group

    # Gradients
    if tokens.gradients:
        gradient_group: dict[str, Any] = {"$type": "gradient"}
        for g in tokens.gradients:
            stops = [{"color": hex_val, "position": pos} for hex_val, pos in g.stops]
            gradient_group[g.name] = {
                "$value": {
                    "type": g.type,
                    "angle": g.angle,
                    "stops": stops,
                },
            }
        result["gradient"] = gradient_group

    return result


def _w3c_color_value(hex_str: str, opacity: float) -> str:
    """Convert hex + opacity to W3C color value.

    Returns ``#RRGGBB`` for fully opaque, ``#RRGGBBAA`` for transparent.
    """
    if opacity >= 1.0:
        return hex_str.upper()
    alpha_hex = f"{round(opacity * 255):02X}"
    return f"{hex_str.upper()}{alpha_hex}"
