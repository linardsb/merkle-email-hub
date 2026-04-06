"""Detect N consecutive structurally similar sections and merge into RepeatingGroup."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.design_sync.figma.layout_analyzer import (
    ColumnLayout,
    EmailSection,
    EmailSectionType,
)

logger = get_logger(__name__)

_SKIP_TYPES: frozenset[EmailSectionType] = frozenset(
    {
        EmailSectionType.DIVIDER,
        EmailSectionType.SPACER,
    }
)


@dataclass(frozen=True)
class SiblingSignature:
    """Structural fingerprint of a section for similarity comparison."""

    image_count: int
    text_count: int
    button_count: int
    has_heading: bool
    column_layout: ColumnLayout
    approx_height_bucket: int  # height // 20


@dataclass(frozen=True)
class RepeatingGroup:
    """A group of structurally similar consecutive sections."""

    sections: list[EmailSection]
    container_bgcolor: str | None = None
    container_padding: tuple[float, float, float, float] | None = None
    pattern_component: str | None = None
    repeat_count: int = 0
    group_confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.repeat_count == 0:
            object.__setattr__(self, "repeat_count", len(self.sections))


_WEIGHTS: dict[str, float] = {
    "image_count": 0.30,
    "text_count": 0.25,
    "button_count": 0.15,
    "has_heading": 0.15,
    "column_layout": 0.10,
    "height_bucket": 0.05,
}


def detect_repeating_groups(
    sections: list[EmailSection],
    *,
    min_group_size: int = 2,
    similarity_threshold: float = 0.8,
) -> list[EmailSection | RepeatingGroup]:
    """Detect consecutive structurally similar sections and merge into groups.

    Returns mixed list: unchanged EmailSection for singles, RepeatingGroup for runs.
    DIVIDER/SPACER sections are never grouped but don't break runs.
    """
    if len(sections) < min_group_size:
        return list(sections)

    signatures = [_compute_signature(s) for s in sections]
    result: list[EmailSection | RepeatingGroup] = []
    i = 0

    while i < len(sections):
        if sections[i].section_type in _SKIP_TYPES:
            result.append(sections[i])
            i += 1
            continue

        # Try to extend a run of similar sections starting at i
        run = [i]
        j = i + 1
        skipped_indices: list[int] = []

        while j < len(sections):
            if sections[j].section_type in _SKIP_TYPES:
                skipped_indices.append(j)
                j += 1
                continue

            sim = _signature_similarity(signatures[i], signatures[j])
            if sim >= similarity_threshold:
                run.append(j)
                j += 1
            else:
                break

        if len(run) >= min_group_size:
            run_sections = [sections[idx] for idx in run]
            avg_sim = _average_pairwise_similarity(
                [signatures[idx] for idx in run],
            )
            container_bg = run_sections[0].bg_color

            group = RepeatingGroup(
                sections=run_sections,
                container_bgcolor=container_bg,
                group_confidence=avg_sim,
            )
            # Emit skipped DIVIDER/SPACER sections before the group
            for sk in skipped_indices:
                if sk < run[0]:
                    result.append(sections[sk])
            result.append(group)
            logger.info(
                "sibling.group_detected",
                repeat_count=len(run_sections),
                confidence=round(avg_sim, 3),
                first_node=run_sections[0].node_id,
            )
            i = j
        else:
            result.append(sections[i])
            i += 1

    return result


def _compute_signature(section: EmailSection) -> SiblingSignature:
    height_bucket = int((section.height or 0) // 20)
    return SiblingSignature(
        image_count=len(section.images),
        text_count=len(section.texts),
        button_count=len(section.buttons),
        has_heading=any(t.is_heading for t in section.texts),
        column_layout=section.column_layout,
        approx_height_bucket=height_bucket,
    )


def _signature_similarity(a: SiblingSignature, b: SiblingSignature) -> float:
    score = 0.0
    score += _WEIGHTS["image_count"] * (1.0 if a.image_count == b.image_count else 0.0)
    score += _WEIGHTS["text_count"] * (1.0 if a.text_count == b.text_count else 0.0)
    score += _WEIGHTS["button_count"] * (1.0 if a.button_count == b.button_count else 0.0)
    score += _WEIGHTS["has_heading"] * (1.0 if a.has_heading == b.has_heading else 0.0)
    score += _WEIGHTS["column_layout"] * (1.0 if a.column_layout == b.column_layout else 0.0)
    score += _WEIGHTS["height_bucket"] * (
        1.0 if abs(a.approx_height_bucket - b.approx_height_bucket) <= 1 else 0.0
    )
    return score


def _average_pairwise_similarity(sigs: list[SiblingSignature]) -> float:
    if len(sigs) < 2:
        return 1.0
    total = sum(
        _signature_similarity(sigs[i], sigs[j])
        for i in range(len(sigs))
        for j in range(i + 1, len(sigs))
    )
    pairs = len(sigs) * (len(sigs) - 1) / 2
    return total / pairs
