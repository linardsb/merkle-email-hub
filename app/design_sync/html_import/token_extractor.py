"""Extract design tokens (colours, typography, spacing) from HTML CSS."""

from __future__ import annotations

import re
from collections import Counter

from app.design_sync.email_design_document import (
    DocumentColor,
    DocumentGradient,
    DocumentGradientStop,
    DocumentSection,
    DocumentSpacing,
    DocumentTokens,
    DocumentTypography,
)
from app.design_sync.html_import.style_parser import (
    normalize_hex_color,
    parse_css_rules,
)

_GRADIENT_RE = re.compile(r"linear-gradient\(\s*([\d.]+)deg\s*,\s*(.+)\)", re.IGNORECASE)
_GRADIENT_STOP_RE = re.compile(r"(#[0-9a-fA-F]{3,8}|rgb\([^)]+\))\s+([\d.]+)%")
_FONT_IMPORT_RE = re.compile(r"@import\s+url\(['\"]?([^'\")\s]+)['\"]?\)", re.IGNORECASE)
_FONT_FACE_RE = re.compile(
    r"@font-face\s*\{[^}]*src:\s*url\(['\"]?([^'\")\s]+)['\"]?\)", re.IGNORECASE
)

_SPACING_NAMES = ("xs", "sm", "md", "lg", "xl", "2xl", "3xl", "4xl")


def extract_tokens(
    style_blocks: list[str],
    sections: list[DocumentSection],
) -> DocumentTokens:
    """Build ``DocumentTokens`` from CSS ``<style>`` blocks and inline styles."""
    # Collect colours
    inline_colors = _collect_inline_colors(sections)
    css_colors = _collect_css_colors(style_blocks)
    combined_colors: Counter[str] = Counter()
    combined_colors.update(inline_colors)
    combined_colors.update(css_colors)

    colors = _assign_color_roles(combined_colors, sections)
    dark_colors = _extract_dark_mode_colors(style_blocks)
    typography = _extract_typography(sections)
    spacing = _extract_spacing(sections)
    gradients = _extract_gradients(sections)

    return DocumentTokens(
        colors=colors,
        dark_colors=dark_colors,
        typography=typography,
        spacing=spacing,
        gradients=gradients,
    )


# ── Colour collection ──────────────────────────────────────────────


def _collect_inline_colors(sections: list[DocumentSection]) -> Counter[str]:
    """Count hex colour occurrences across all section content."""
    counts: Counter[str] = Counter()
    for section in sections:
        if section.background_color:
            normed = normalize_hex_color(section.background_color)
            if normed:
                counts[normed] += 1
        # Note: text/button colors were extracted at DOM parse time
        # and are already embedded in DocumentText/DocumentButton fields
    return counts


def _collect_css_colors(style_blocks: list[str]) -> Counter[str]:
    """Count hex colours in ``<style>`` blocks."""
    counts: Counter[str] = Counter()
    for block in style_blocks:
        rules = parse_css_rules(block)
        for rule in rules:
            if rule.is_dark_mode:
                continue  # Dark mode handled separately
            for prop, value in rule.properties.items():
                if "color" in prop or prop in ("background", "border-color"):
                    normed = normalize_hex_color(value)
                    if normed:
                        counts[normed] += 1
    return counts


def _assign_color_roles(
    color_counts: Counter[str], sections: list[DocumentSection]
) -> list[DocumentColor]:
    """Assign semantic roles to collected colours by frequency and usage."""
    if not color_counts:
        return []

    # Separate background colours from sections
    bg_colors: Counter[str] = Counter()

    for section in sections:
        if section.background_color:
            normed = normalize_hex_color(section.background_color)
            if normed:
                bg_colors[normed] += 1

    # Most common colours
    ordered = color_counts.most_common()
    assigned: list[DocumentColor] = []
    used_roles: set[str] = set()

    # Assign background
    if bg_colors:
        top_bg = bg_colors.most_common(1)[0][0]
        assigned.append(DocumentColor(name="background", hex=top_bg))
        used_roles.add("background")

    # Assign text colours — common dark colours
    role_order = ["body_text", "heading_text", "primary", "secondary"]
    accent_idx = 0

    for hex_val, _count in ordered:
        if hex_val in {c.hex for c in assigned}:
            continue
        if role_order:
            role = role_order.pop(0)
        else:
            accent_idx += 1
            role = f"accent_{accent_idx}"

        assigned.append(DocumentColor(name=role, hex=hex_val))

        if len(assigned) >= 10:
            break

    return assigned


# ── Dark mode ──────────────────────────────────────────────────────


def _extract_dark_mode_colors(style_blocks: list[str]) -> list[DocumentColor]:
    """Parse ``@media (prefers-color-scheme: dark)`` rules."""
    dark_colors: list[DocumentColor] = []
    seen: set[str] = set()

    for block in style_blocks:
        rules = parse_css_rules(block)
        for rule in rules:
            if not rule.is_dark_mode:
                continue
            for prop, value in rule.properties.items():
                if "color" in prop or prop in ("background", "background-color"):
                    normed = normalize_hex_color(value)
                    if normed and normed not in seen:
                        seen.add(normed)
                        role = "dark_background" if "background" in prop else "dark_text"
                        if role in {c.name for c in dark_colors}:
                            role = f"dark_accent_{len(dark_colors)}"
                        dark_colors.append(DocumentColor(name=role, hex=normed))

    return dark_colors


# ── Typography ─────────────────────────────────────────────────────


def _extract_typography(sections: list[DocumentSection]) -> list[DocumentTypography]:
    """Extract distinct typography tokens from section text blocks."""
    # Collect unique (family, size, weight) combos
    combos: dict[tuple[str, float, int], int] = {}

    for section in sections:
        for text in section.texts:
            family = text.font_family or "Arial"
            size = text.font_size or 16.0
            weight = text.font_weight or 400
            key = (family, size, weight)
            combos[key] = combos.get(key, 0) + 1
        for col in section.columns:
            for text in col.texts:
                family = text.font_family or "Arial"
                size = text.font_size or 16.0
                weight = text.font_weight or 400
                key = (family, size, weight)
                combos[key] = combos.get(key, 0) + 1

    if not combos:
        return []

    # Sort by size descending
    sorted_combos = sorted(combos.items(), key=lambda x: (-x[0][1], -x[1]))

    result: list[DocumentTypography] = []
    heading_assigned = False
    body_assigned = False

    for (family, size, weight), _count in sorted_combos:
        if not heading_assigned and size >= 20.0:
            name = "heading"
            heading_assigned = True
        elif not body_assigned and size < 20.0:
            name = "body"
            body_assigned = True
        else:
            name = f"text_{int(size)}px"

        result.append(
            DocumentTypography(
                name=name,
                family=family,
                weight=str(weight),
                size=size,
                line_height=round(size * 1.4, 1),
            )
        )

        if len(result) >= 8:
            break

    return result


# ── Spacing ────────────────────────────────────────────────────────


def _extract_spacing(sections: list[DocumentSection]) -> list[DocumentSpacing]:
    """Derive a spacing scale from padding values in sections."""
    values: set[float] = set()

    for section in sections:
        if section.padding:
            for val in (
                section.padding.top,
                section.padding.right,
                section.padding.bottom,
                section.padding.left,
            ):
                if val > 0:
                    values.add(val)
        if section.spacing_after is not None and section.spacing_after > 0:
            values.add(section.spacing_after)

    if not values:
        return []

    sorted_values = sorted(values)
    result: list[DocumentSpacing] = []
    for idx, val in enumerate(sorted_values[:8]):
        name = _SPACING_NAMES[idx] if idx < len(_SPACING_NAMES) else f"space_{idx}"
        result.append(DocumentSpacing(name=name, value=val))

    return result


# ── Gradients ──────────────────────────────────────────────────────


def _extract_gradients(sections: list[DocumentSection]) -> list[DocumentGradient]:
    """Detect linear-gradient() in section backgrounds."""
    results: list[DocumentGradient] = []
    idx = 0

    for section in sections:
        if not section.background_color:
            continue
        m = _GRADIENT_RE.search(section.background_color)
        if not m:
            continue

        angle = float(m.group(1))
        stops_str = m.group(2)
        stops: list[DocumentGradientStop] = []

        for sm in _GRADIENT_STOP_RE.finditer(stops_str):
            color = normalize_hex_color(sm.group(1))
            if color:
                stops.append(DocumentGradientStop(hex=color, position=float(sm.group(2))))

        if len(stops) >= 2:
            idx += 1
            results.append(
                DocumentGradient(
                    name=f"gradient_{idx}",
                    type="linear",
                    angle=angle,
                    stops=tuple(stops),
                    fallback_hex=stops[0].hex,
                )
            )

    return results


# ── Web fonts ──────────────────────────────────────────────────────


def detect_web_fonts(style_blocks: list[str]) -> list[str]:
    """Find web font URLs from ``@import`` and ``@font-face`` rules."""
    urls: list[str] = []
    seen: set[str] = set()

    for block in style_blocks:
        for m in _FONT_IMPORT_RE.finditer(block):
            url = m.group(1)
            if url not in seen:
                seen.add(url)
                urls.append(url)
        for m in _FONT_FACE_RE.finditer(block):
            url = m.group(1)
            if url not in seen:
                seen.add(url)
                urls.append(url)

    return urls
