"""Design system token mapper for imported templates.

Maps extracted tokens from uploaded HTML against a project's design system,
producing a diff that shows what will be replaced at build time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.templates.models import DefaultTokens
from app.core.logging import get_logger
from app.projects.design_system import (
    DesignSystem,
    resolve_color_map,
    resolve_font_map,
    resolve_font_size_map,
    resolve_spacing_map,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class TokenDiff:
    """Describes how an extracted token relates to the project's design system."""

    property: str
    role: str
    imported_value: str
    design_system_value: str
    action: str  # "will_replace", "compatible", "no_override"


class DesignSystemMapper:
    """Maps extracted template tokens against a project design system."""

    def __init__(self, design_system: DesignSystem | None) -> None:
        self._ds = design_system
        if design_system:
            self._font_map = resolve_font_map(design_system)
            self._font_size_map = resolve_font_size_map(design_system)
            self._spacing_map = resolve_spacing_map(design_system)
            self._color_map = resolve_color_map(design_system)
        else:
            self._font_map = {}
            self._font_size_map = {}
            self._spacing_map = {}
            self._color_map = {}

    def map_tokens(self, extracted: DefaultTokens) -> DefaultTokens:
        """Map extracted tokens to design system equivalents.

        The *extracted* values stay in DefaultTokens (they are the "find" values
        for the assembler's find-replace). The design system values go into
        DesignTokens at build time.

        If no design system is configured, returns extracted unchanged.
        """
        if not self._ds:
            return extracted

        mapped_fonts = dict(extracted.fonts)
        for role, font in extracted.fonts.items():
            ds_font = self._font_map.get(role)
            if ds_font and ds_font != font:
                # Keep extracted value — it becomes the "find" target
                mapped_fonts[role] = font

        mapped_sizes = dict(extracted.font_sizes)
        for role, size in extracted.font_sizes.items():
            nearest = self._find_nearest_size(size, self._font_size_map)
            if nearest:
                mapped_sizes[role] = size

        mapped_spacing = dict(extracted.spacing)
        for role, spacing in extracted.spacing.items():
            nearest = self._find_nearest_size(spacing, self._spacing_map)
            if nearest:
                mapped_spacing[role] = spacing

        return DefaultTokens(
            colors=dict(extracted.colors),
            fonts=mapped_fonts,
            font_sizes=mapped_sizes,
            spacing=mapped_spacing,
            font_weights=dict(extracted.font_weights),
            line_heights=dict(extracted.line_heights),
            letter_spacings=dict(extracted.letter_spacings),
            responsive=dict(extracted.responsive),
            responsive_breakpoints=extracted.responsive_breakpoints,
        )

    def generate_diff(self, extracted: DefaultTokens, _mapped: DefaultTokens) -> list[TokenDiff]:
        """Compare extracted vs mapped tokens to produce a human-readable diff."""
        if not self._ds:
            return []

        diffs: list[TokenDiff] = []

        # Fonts
        for role, ext_val in extracted.fonts.items():
            ds_val = self._font_map.get(role)
            if ds_val is None:
                diffs.append(TokenDiff("font-family", role, ext_val, "", "no_override"))
            elif ds_val == ext_val:
                diffs.append(TokenDiff("font-family", role, ext_val, ds_val, "compatible"))
            else:
                diffs.append(TokenDiff("font-family", role, ext_val, ds_val, "will_replace"))

        # Font sizes
        for role, ext_val in extracted.font_sizes.items():
            ds_val = self._find_nearest_size(ext_val, self._font_size_map)
            if ds_val is None:
                diffs.append(TokenDiff("font-size", role, ext_val, "", "no_override"))
            elif ds_val == ext_val:
                diffs.append(TokenDiff("font-size", role, ext_val, ds_val, "compatible"))
            else:
                diffs.append(TokenDiff("font-size", role, ext_val, ds_val, "will_replace"))

        # Spacing
        for role, ext_val in extracted.spacing.items():
            ds_val = self._find_nearest_size(ext_val, self._spacing_map)
            if ds_val is None:
                diffs.append(TokenDiff("spacing", role, ext_val, "", "no_override"))
            elif ds_val == ext_val:
                diffs.append(TokenDiff("spacing", role, ext_val, ds_val, "compatible"))
            else:
                diffs.append(TokenDiff("spacing", role, ext_val, ds_val, "will_replace"))

        # Font weights
        for role, ext_val in extracted.font_weights.items():
            diffs.append(TokenDiff("font-weight", role, ext_val, "", "no_override"))

        # Line heights
        for role, ext_val in extracted.line_heights.items():
            diffs.append(TokenDiff("line-height", role, ext_val, "", "no_override"))

        # Letter spacings
        for role, ext_val in extracted.letter_spacings.items():
            diffs.append(TokenDiff("letter-spacing", role, ext_val, "", "no_override"))

        return diffs

    @staticmethod
    def _find_nearest_size(value: str, size_map: dict[str, str]) -> str | None:
        """Find the nearest size in the design system map by numeric proximity."""
        if not size_map:
            return None
        val_num = _parse_numeric(value)
        if val_num is None:
            return None

        best_match: str | None = None
        best_distance = float("inf")
        for ds_val in size_map.values():
            ds_num = _parse_numeric(ds_val)
            if ds_num is None:
                continue
            distance = abs(val_num - ds_num)
            if distance < best_distance:
                best_distance = distance
                best_match = ds_val
        return best_match


def _parse_numeric(value: str) -> float | None:
    """Extract numeric portion from a CSS value like '32px' or '1.5rem'."""
    m = re.match(r"^([\d.]+)", value.strip())
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None
