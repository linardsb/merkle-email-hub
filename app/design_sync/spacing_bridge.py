"""Bridge Figma/Penpot layout spacing to DefaultTokens format."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from app.design_sync.figma.layout_analyzer import DesignLayoutDescription, TextBlock


@dataclass(frozen=True)
class TypographyTokens:
    """Typography tokens extracted from Figma/Penpot layout analysis."""

    font_sizes: dict[str, str] = field(default_factory=dict[str, str])
    fonts: dict[str, str] = field(default_factory=dict[str, str])
    font_weights: dict[str, str] = field(default_factory=dict[str, str])
    line_heights: dict[str, str] = field(default_factory=dict[str, str])


def figma_spacing_to_tokens(layout: DesignLayoutDescription) -> dict[str, str]:
    """Convert per-section spacing map to DefaultTokens.spacing format.

    Uses most-common values across sections as defaults.
    """
    padding_values: list[str] = []
    gap_values: list[str] = []

    for section in layout.sections:
        for side in ("padding_top", "padding_right", "padding_bottom", "padding_left"):
            val = getattr(section, side, None)
            if val is not None:
                padding_values.append(f"{int(val)}px")
        if section.item_spacing is not None:
            gap_values.append(f"{int(section.item_spacing)}px")

    result: dict[str, str] = {}
    if padding_values:
        result["section_padding"] = Counter(padding_values).most_common(1)[0][0]
    if gap_values:
        result["element_gap"] = Counter(gap_values).most_common(1)[0][0]

    return result


def figma_typography_to_tokens(layout: DesignLayoutDescription) -> TypographyTokens:
    """Extract typography tokens from layout TextBlocks."""
    all_texts: list[TextBlock] = []
    for section in layout.sections:
        all_texts.extend(section.texts)

    heading_texts = [t for t in all_texts if t.is_heading]
    body_texts = [t for t in all_texts if not t.is_heading]

    font_sizes: dict[str, str] = {}
    fonts: dict[str, str] = {}
    font_weights: dict[str, str] = {}
    line_heights: dict[str, str] = {}

    # Font sizes
    heading_sizes = [t.font_size for t in heading_texts if t.font_size is not None]
    body_sizes = [t.font_size for t in body_texts if t.font_size is not None]
    if heading_sizes:
        font_sizes["heading"] = f"{int(Counter(heading_sizes).most_common(1)[0][0])}px"
    if body_sizes:
        font_sizes["body"] = f"{int(Counter(body_sizes).most_common(1)[0][0])}px"

    # Font families
    heading_families = [t.font_family for t in heading_texts if t.font_family]
    body_families = [t.font_family for t in body_texts if t.font_family]
    if heading_families:
        fonts["heading"] = Counter(heading_families).most_common(1)[0][0]
    if body_families:
        fonts["body"] = Counter(body_families).most_common(1)[0][0]

    # Font weights
    heading_weights = [t.font_weight for t in heading_texts if t.font_weight is not None]
    body_weights = [t.font_weight for t in body_texts if t.font_weight is not None]
    if heading_weights:
        font_weights["heading"] = str(Counter(heading_weights).most_common(1)[0][0])
    if body_weights:
        font_weights["body"] = str(Counter(body_weights).most_common(1)[0][0])

    # Line heights
    heading_lh = [t.line_height for t in heading_texts if t.line_height is not None]
    body_lh = [t.line_height for t in body_texts if t.line_height is not None]
    if heading_lh:
        line_heights["heading"] = f"{Counter(heading_lh).most_common(1)[0][0]:.0f}px"
    if body_lh:
        line_heights["body"] = f"{Counter(body_lh).most_common(1)[0][0]:.0f}px"

    return TypographyTokens(
        font_sizes=font_sizes,
        fonts=fonts,
        font_weights=font_weights,
        line_heights=line_heights,
    )
