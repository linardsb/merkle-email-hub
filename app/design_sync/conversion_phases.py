"""Phase outputs for the component-based conversion pipeline.

`_convert_with_components` is split into three phases:
- `_match_phase`  → `MatchPhase`  (sibling detection + component matching)
- `_render_phase` → `RenderPhase` (per-section render loop + bgcolor propagation)
- `_assemble_phase` → `ConversionResult` (style block + shell + quality contracts)

Tree-bridge is handled in the orchestrator before `_render_phase`.
Verification (`_apply_verification`) is a separate concern of the MJML path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.design_sync.component_matcher import ComponentMatch
    from app.design_sync.figma.layout_analyzer import EmailSection
    from app.design_sync.sibling_detector import RepeatingGroup


@dataclass(frozen=True)
class MatchPhase:
    """Output of `_match_phase`.

    Carries flat matches for the renderer plus the grouped view for the
    tree-bridge path which needs the original group structure.
    """

    matches: list[ComponentMatch]
    grouped_sections: list[EmailSection | RepeatingGroup]
    group_map: dict[int, RepeatingGroup]


@dataclass(frozen=True)
class RenderPhase:
    """Output of `_render_phase`.

    `section_parts` is the post-bgcolor-propagation list ready for join.
    `warnings` is the (possibly mutated) list passed in — custom-generation
    appends entries as a side effect; surfaced here for the assemble phase.
    """

    section_parts: list[str]
    images: list[dict[str, str]]
    hit_count: int
    miss_count: int
    warnings: list[str] = field(default_factory=list[str])
