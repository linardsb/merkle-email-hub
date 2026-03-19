"""Extract DefaultTokens from analyzed inline style data."""

from __future__ import annotations

from collections import Counter

from app.ai.templates.models import DefaultTokens
from app.templates.upload.analyzer import TokenInfo


class TokenExtractor:
    """Builds DefaultTokens from analyzed HTML inline styles."""

    def extract(self, token_info: TokenInfo) -> DefaultTokens:
        """Convert raw color/font/spacing analysis into DefaultTokens.

        Role inference: frequency-based for colors, context-based for fonts.
        """
        colors = self._resolve_colors(token_info)
        fonts = self._resolve_fonts(token_info)
        font_sizes = self._resolve_font_sizes(token_info)
        spacing = self._resolve_spacing(token_info)

        return DefaultTokens(
            colors=colors,
            fonts=fonts,
            font_sizes=font_sizes,
            spacing=spacing,
        )

    def _resolve_colors(self, token_info: TokenInfo) -> dict[str, str]:
        """Assign semantic color roles from frequency analysis."""
        colors: dict[str, str] = {}

        bg_colors = token_info.colors.get("background", [])
        text_colors = token_info.colors.get("text", [])
        all_colors = token_info.colors.get("all", [])

        if bg_colors:
            colors["background"] = Counter(bg_colors).most_common(1)[0][0]
        if text_colors:
            counted = Counter(text_colors).most_common(3)
            colors["text"] = counted[0][0]
            if len(counted) >= 2:
                colors["secondary"] = counted[1][0]

        # CTA color: look for colors on buttons (not the most common bg)
        if all_colors:
            all_counted = Counter(all_colors).most_common(5)
            for color, _count in all_counted:
                if color != colors.get("background") and color != colors.get("text"):
                    colors.setdefault("cta", color)
                    break

        return colors

    def _resolve_fonts(self, token_info: TokenInfo) -> dict[str, str]:
        """Assign heading vs body font stacks."""
        fonts: dict[str, str] = {}
        heading_fonts = token_info.fonts.get("heading", [])
        body_fonts = token_info.fonts.get("body", [])

        if heading_fonts:
            fonts["heading"] = Counter(heading_fonts).most_common(1)[0][0]
        if body_fonts:
            fonts["body"] = Counter(body_fonts).most_common(1)[0][0]

        return fonts

    def _resolve_font_sizes(self, token_info: TokenInfo) -> dict[str, str]:
        """Map font sizes to semantic roles."""
        sizes: dict[str, str] = {}
        all_sizes = token_info.font_sizes.get("all", [])
        if not all_sizes:
            return sizes

        # Sort unique sizes by numeric value
        unique = sorted(set(all_sizes), key=_numeric_size, reverse=True)
        if unique:
            sizes["heading"] = unique[0]
        if len(unique) >= 2:
            sizes["body"] = unique[1]
        if len(unique) >= 3:
            sizes["small"] = unique[-1]

        return sizes

    def _resolve_spacing(self, token_info: TokenInfo) -> dict[str, str]:
        """Extract common spacing values."""
        spacing: dict[str, str] = {}
        paddings = token_info.spacing.get("padding", [])
        if paddings:
            counted = Counter(paddings).most_common(2)
            spacing["section"] = counted[0][0]
            if len(counted) >= 2:
                spacing["element"] = counted[1][0]
        return spacing


def _numeric_size(size_str: str) -> float:
    """Extract numeric value from CSS size string."""
    import re

    match = re.match(r"(\d+(?:\.\d+)?)", size_str)
    return float(match.group(1)) if match else 0.0
