"""Persist converter quality metadata to agent memory.

After each conversion, stores quality warnings and match confidence data as
semantic memory entries so agents can recall past conversion issues for similar
designs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.design_sync.converter_service import ConversionResult

logger = get_logger(__name__)

_MAX_CONTENT_LENGTH = 4000
_CLEAN_CONFIDENCE_THRESHOLD = 0.8


def _should_persist(result: ConversionResult) -> bool:
    """Skip clean conversions — only persist when there are quality issues."""
    return bool(result.quality_warnings) or any(
        c < _CLEAN_CONFIDENCE_THRESHOLD for c in result.match_confidences.values()
    )


def format_conversion_quality(
    result: ConversionResult,
) -> str | None:
    """Format a conversion quality report as a memory content string.

    Returns None if the conversion is clean (no warnings, high confidence).
    """
    if not _should_persist(result):
        return None

    lines: list[str] = [
        f"Conversion quality report (sections={result.sections_count}, "
        f"warnings={len(result.quality_warnings)}):",
    ]

    # Group warnings by category
    for w in result.quality_warnings:
        lines.append(f"- {w.category} ({w.severity}): {w.message}")

    # Low-confidence sections
    low_confidence = [idx for idx, conf in result.match_confidences.items() if conf < 0.6]
    if low_confidence:
        avg_low = sum(result.match_confidences[i] for i in low_confidence) / len(low_confidence)
        lines.append(f"Low-confidence matches: sections {low_confidence} (avg {avg_low:.2f})")

    # Design tokens
    if result.design_tokens_used:
        token_parts: list[str] = []
        if "primary_color" in result.design_tokens_used:
            token_parts.append(str(result.design_tokens_used["primary_color"]))
        if "font_family" in result.design_tokens_used:
            token_parts.append(str(result.design_tokens_used["font_family"]))
        if token_parts:
            lines.append(f"Design tokens: {', '.join(token_parts)}")

    lines.append(f"Source: {result.figma_url or 'unknown'}")

    content = "\n".join(lines)
    if len(content) > _MAX_CONTENT_LENGTH:
        content = content[: _MAX_CONTENT_LENGTH - 3] + "..."
    return content


def build_conversion_metadata(
    result: ConversionResult,
    connection_id: str | None,
) -> dict[str, Any]:
    """Build metadata dict for the memory entry."""
    low_confidence_sections = [idx for idx, conf in result.match_confidences.items() if conf < 0.6]
    confidences = list(result.match_confidences.values())
    avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0
    categories = sorted({w.category for w in result.quality_warnings})

    return {
        "source": "converter_quality",
        "connection_id": connection_id,
        "figma_url": result.figma_url,
        "node_id": result.node_id,
        "sections_count": result.sections_count,
        "warning_count": len(result.quality_warnings),
        "warning_categories": categories,
        "avg_match_confidence": round(avg_confidence, 4),
        "low_confidence_sections": low_confidence_sections,
        "has_quality_issues": True,
    }


async def persist_conversion_quality(
    result: ConversionResult,
    connection_id: str | None,
    project_id: int | None,
) -> None:
    """Persist conversion quality data as a semantic memory entry.

    Fire-and-forget — exceptions are logged but never propagate.
    """
    try:
        settings = get_settings()
        if not settings.design_sync.conversion_memory_enabled:
            return

        content = format_conversion_quality(result)
        if content is None:
            return

        metadata = build_conversion_metadata(result, connection_id)

        from app.core.database import get_db_context
        from app.knowledge.embedding import get_embedding_provider
        from app.memory.schemas import MemoryCreate
        from app.memory.service import MemoryService

        async with get_db_context() as db:
            embedding_provider = get_embedding_provider(settings)
            service = MemoryService(db, embedding_provider)
            await service.store(
                MemoryCreate(
                    agent_type="design_sync",
                    memory_type="semantic",
                    content=content,
                    project_id=project_id,
                    metadata=metadata,
                    is_evergreen=False,
                ),
            )

        logger.info(
            "converter_memory.persisted",
            connection_id=connection_id,
            warning_count=len(result.quality_warnings),
            project_id=project_id,
        )
    except Exception:
        logger.warning(
            "converter_memory.persist_failed",
            connection_id=connection_id,
            exc_info=True,
        )
