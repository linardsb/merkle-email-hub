"""Extract DefaultTokens from analyzed inline style data."""

from __future__ import annotations

import re
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
        font_weights = self._resolve_font_weights(token_info)
        line_heights = self._resolve_line_heights(token_info)
        letter_spacings = self._resolve_letter_spacings(token_info)
        responsive, breakpoints = self._resolve_responsive(token_info)

        return DefaultTokens(
            colors=colors,
            fonts=fonts,
            font_sizes=font_sizes,
            spacing=spacing,
            font_weights=font_weights,
            line_heights=line_heights,
            letter_spacings=letter_spacings,
            responsive=responsive,
            responsive_breakpoints=breakpoints,
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

        # Color roles from element context
        for role, values in token_info.color_roles.items():
            if values and role not in colors:
                colors[role] = Counter(values).most_common(1)[0][0]

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

    def _resolve_font_weights(self, token_info: TokenInfo) -> dict[str, str]:
        """Assign heading vs body font weight from frequency analysis."""
        weights: dict[str, str] = {}
        heading = token_info.font_weights.get("heading", [])
        body = token_info.font_weights.get("body", [])
        if heading:
            weights["heading"] = Counter(heading).most_common(1)[0][0]
        if body:
            weights["body"] = Counter(body).most_common(1)[0][0]
        return weights

    def _resolve_line_heights(self, token_info: TokenInfo) -> dict[str, str]:
        """Assign heading vs body line height from frequency analysis."""
        heights: dict[str, str] = {}
        heading = token_info.line_heights.get("heading", [])
        body = token_info.line_heights.get("body", [])
        if heading:
            heights["heading"] = Counter(heading).most_common(1)[0][0]
        if body:
            heights["body"] = Counter(body).most_common(1)[0][0]
        return heights

    def _resolve_letter_spacings(self, token_info: TokenInfo) -> dict[str, str]:
        """Extract letter-spacing values."""
        spacings: dict[str, str] = {}
        all_ls = token_info.letter_spacings.get("all", [])
        if all_ls:
            spacings["heading"] = Counter(all_ls).most_common(1)[0][0]
        return spacings

    def _resolve_responsive(self, token_info: TokenInfo) -> tuple[dict[str, str], tuple[str, ...]]:
        """Flatten responsive token data into role-based dict."""
        result: dict[str, str] = {}
        breakpoints = token_info.responsive_breakpoints

        if not breakpoints or not token_info.responsive:
            return result, ()

        # Use first breakpoint as "mobile"
        bp = breakpoints[0]
        bp_data = token_info.responsive.get(bp, {})

        mobile_sizes = bp_data.get("font_sizes", [])
        if mobile_sizes:
            unique = sorted(set(mobile_sizes), key=_numeric_size, reverse=True)
            if unique:
                result["mobile_heading_size"] = unique[0]
            if len(unique) >= 2:
                result["mobile_body_size"] = unique[-1]

        mobile_spacing = bp_data.get("spacing", [])
        if mobile_spacing:
            result["mobile_section_padding"] = Counter(mobile_spacing).most_common(1)[0][0]

        result["breakpoint"] = bp
        return result, tuple(breakpoints)


def _numeric_size(size_str: str) -> float:
    """Extract numeric value from CSS size string."""
    match = re.match(r"(\d+(?:\.\d+)?)", size_str)
    return float(match.group(1)) if match else 0.0
