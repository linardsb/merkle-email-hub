"""Stage 8: Brand repair — deterministic off-palette color correction and element injection."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from app.qa_engine.repair.pipeline import RepairResult

if TYPE_CHECKING:
    from app.projects.design_system import DesignSystem

_HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}\b")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB to (R, G, B) tuple."""
    h = hex_color.lstrip("#").lower()
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    """Euclidean distance in RGB space."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2, strict=True)))


def _find_nearest_palette_color(
    color: str,
    palette_colors: list[str],
) -> str | None:
    """Find nearest palette color by RGB Euclidean distance.

    Returns None if palette is empty.
    """
    if not palette_colors:
        return None
    target = _hex_to_rgb(color)
    best_match = palette_colors[0]
    best_dist = _color_distance(target, _hex_to_rgb(palette_colors[0]))
    for pc in palette_colors[1:]:
        dist = _color_distance(target, _hex_to_rgb(pc))
        if dist < best_dist:
            best_dist = dist
            best_match = pc
    return best_match


def _escape_html(text: str) -> str:
    """Minimal HTML entity escaping for trusted admin content."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(text: str) -> str:
    """Escape for HTML attribute values."""
    return _escape_html(text).replace('"', "&quot;")


class BrandRepair:
    """Deterministic brand repair — correct off-palette colors, inject missing elements.

    Requires a DesignSystem to operate. When no design system is provided,
    this stage is a no-op (returns HTML unchanged).
    """

    def __init__(self, design_system: DesignSystem | None = None) -> None:
        self._ds = design_system

    @property
    def name(self) -> str:
        return "brand"

    def repair(self, html: str) -> RepairResult:
        if self._ds is None:
            return RepairResult(html=html)

        repairs: list[str] = []
        warnings: list[str] = []
        result = html

        # Phase 1: Color correction
        result, color_repairs = self._repair_colors(result)
        repairs.extend(color_repairs)

        # Phase 2: Footer verification/injection
        result, footer_actions = self._repair_footer(result)
        repairs.extend(r for r in footer_actions if not r.startswith("warn:"))
        warnings.extend(r[5:] for r in footer_actions if r.startswith("warn:"))

        # Phase 3: Logo verification/injection
        result, logo_actions = self._repair_logo(result)
        repairs.extend(r for r in logo_actions if not r.startswith("warn:"))
        warnings.extend(r[5:] for r in logo_actions if r.startswith("warn:"))

        return RepairResult(html=result, repairs_applied=repairs, warnings=warnings)

    def _repair_colors(self, html: str) -> tuple[str, list[str]]:
        """Replace off-palette hex colors with nearest palette match."""
        from app.projects.design_system import resolve_color_map

        if self._ds is None:  # pragma: no cover — guarded by repair()
            return html, []
        color_map = resolve_color_map(self._ds)
        palette_colors = list(dict.fromkeys(color_map.values()))  # unique, order-preserved

        if not palette_colors:
            return html, []

        palette_set = {c.lower() for c in palette_colors}
        repairs: list[str] = []

        def _replace_color(match: re.Match[str]) -> str:
            color = match.group(0).lower()
            if color in palette_set:
                return color
            nearest = _find_nearest_palette_color(color, palette_colors)
            if nearest and nearest.lower() != color:
                repairs.append(f"color_{color}_to_{nearest}")
                return nearest
            return color

        result = _HEX_COLOR_RE.sub(_replace_color, html)
        return result, repairs

    def _repair_footer(self, html: str) -> tuple[str, list[str]]:
        """Verify footer presence; inject from DesignSystem if missing."""
        if self._ds is None:  # pragma: no cover — guarded by repair()
            return html, []
        actions: list[str] = []

        has_footer = bool(re.search(r'<footer[\s>]|class="[^"]*footer[^"]*"', html, re.IGNORECASE))

        if has_footer or self._ds.footer is None:
            return html, actions

        # Footer is missing and we have FooterConfig — inject before </body>
        fc = self._ds.footer
        footer_html = (
            f'\n<footer style="text-align:center; padding:20px; '
            f'font-size:12px; color:{self._ds.palette.text};">\n'
            f"  <p>{_escape_html(fc.company_name)}</p>\n"
        )
        if fc.address:
            footer_html += f"  <p>{_escape_html(fc.address)}</p>\n"
        if fc.legal_text:
            footer_html += f"  <p>{_escape_html(fc.legal_text)}</p>\n"
        footer_html += "</footer>\n"

        body_close = re.search(r"</body\s*>", html, re.IGNORECASE)
        if body_close:
            html = html[: body_close.start()] + footer_html + html[body_close.start() :]
            actions.append("injected_footer")
        else:
            actions.append("warn:footer_missing_no_body_tag")

        return html, actions

    def _repair_logo(self, html: str) -> tuple[str, list[str]]:
        """Verify logo presence; inject from DesignSystem if missing."""
        if self._ds is None:  # pragma: no cover — guarded by repair()
            return html, []
        actions: list[str] = []

        has_logo = bool(
            re.search(r'<img[^>]*(?:class|alt|id|src)="[^"]*logo[^"]*"', html, re.IGNORECASE)
        )

        if has_logo or self._ds.logo is None:
            return html, actions

        # Logo missing and we have LogoConfig — inject after <body> opening
        lc = self._ds.logo
        logo_html = (
            f'\n<div style="text-align:center; padding:10px;">'
            f'<img src="{_escape_attr(lc.url)}" alt="{_escape_attr(lc.alt_text)}" '
            f'width="{lc.width}" height="{lc.height}" '
            f'style="display:inline-block; max-width:100%;" />'
            f"</div>\n"
        )

        body_open = re.search(r"<body[^>]*>", html, re.IGNORECASE)
        if body_open:
            insert_pos = body_open.end()
            html = html[:insert_pos] + logo_html + html[insert_pos:]
            actions.append("injected_logo")
        else:
            actions.append("warn:logo_missing_no_body_tag")

        return html, actions
