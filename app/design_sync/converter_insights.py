"""Extract converter low-confidence matches as cross-agent insights.

When the converter produces low-confidence component matches, generates
AgentInsight entries targeting the Scaffolder so it can adjust template
selection strategy for similar designs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import groupby
from typing import TYPE_CHECKING

from app.ai.blueprints.insight_bus import AgentInsight, persist_insights
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.design_sync.converter_service import ConversionResult

logger = get_logger(__name__)


def extract_conversion_insights(
    result: ConversionResult,
) -> list[AgentInsight]:
    """Scan match_confidences for entries below threshold.

    Groups nearby low-confidence sections by section type (from layout)
    to avoid insight flooding.
    """
    settings = get_settings()
    threshold = settings.design_sync.low_match_confidence_threshold

    low_sections = sorted(
        (idx, conf) for idx, conf in result.match_confidences.items() if conf < threshold
    )
    if not low_sections:
        return []

    # Build section type lookup from layout
    section_types: dict[int, str] = {}
    if result.layout:
        for i, section in enumerate(result.layout.sections):
            section_types[i] = section.section_type.value

    now = datetime.now(UTC)
    insights: list[AgentInsight] = []

    # Group by section type to avoid flooding
    def _section_type(item: tuple[int, float]) -> str:
        return section_types.get(item[0], "unknown")

    for section_type, group in groupby(low_sections, key=_section_type):
        items = list(group)
        indices = [idx for idx, _ in items]
        avg_conf = sum(conf for _, conf in items) / len(items)

        if len(items) == 1:
            idx, conf = items[0]
            text = (
                f"Section {idx} ({section_type}) matched with "
                f"{conf:.0%} confidence. Consider alternative templates "
                f"for this layout pattern."
            )
        else:
            text = (
                f"Sections {indices} ({section_type}) matched with "
                f"avg {avg_conf:.0%} confidence. Consider alternative "
                f"templates for this layout pattern."
            )

        insights.append(
            AgentInsight(
                source_agent="design_sync",
                target_agents=("scaffolder",),
                client_ids=(),
                insight=text,
                category="conversion",
                confidence=1.0 - avg_conf,
                evidence_count=1,
                first_seen=now,
                last_seen=now,
            )
        )

    return insights


async def persist_conversion_insights(
    result: ConversionResult,
    connection_id: str | None,
    project_id: int | None,
) -> int:
    """Extract and persist conversion insights. Fire-and-forget."""
    try:
        settings = get_settings()
        if not settings.design_sync.conversion_memory_enabled:
            return 0

        insights = extract_conversion_insights(result)
        if not insights:
            return 0

        count = await persist_insights(insights, project_id)
        logger.info(
            "converter_insights.persisted",
            count=count,
            connection_id=connection_id,
        )
        return count
    except Exception:
        logger.warning(
            "converter_insights.persist_failed",
            connection_id=connection_id,
            exc_info=True,
        )
        return 0
