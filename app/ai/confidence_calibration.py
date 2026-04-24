"""Per-agent confidence calibration — adjusts thresholds based on actual outcomes.

Tracks whether agent confidence scores correlate with actual QA outcomes.
If an agent is overconfident (reports high confidence but frequently fails),
the effective threshold is raised via a discount factor.

Enabled via BLUEPRINT__CONFIDENCE_CALIBRATION_ENABLED=true (default: false).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_DISCOUNT = 1.0
MIN_CALIBRATION_SAMPLES = 10
_CONFIDENCE_REVIEW_THRESHOLD = 0.5  # mirrors engine constant


@dataclass(frozen=True)
class CalibrationResult:
    """Per-agent calibration data."""

    agent_name: str
    discount: float  # multiply raw confidence by this (< 1.0 = overconfident)
    sample_count: int
    effective_threshold: float  # adjusted CONFIDENCE_REVIEW_THRESHOLD


async def compute_calibration(
    agent_name: str,
    project_id: int | None,
    db: AsyncSession,
) -> CalibrationResult:
    """Compute confidence calibration from handoff + outcome memory.

    Queries episodic memories with source="blueprint_handoff" for this agent,
    extracts confidence from metadata, cross-references run_id with outcome
    memories (source="blueprint_outcome") to determine actual pass/fail.

    If agent reports avg 0.8 confidence but only passes 50%,
    discount = 0.50 / 0.80 = 0.625.
    effective_threshold = 0.5 / discount = 0.8 (needs higher raw confidence).
    """
    from app.core.config import get_settings
    from app.knowledge.embedding import get_embedding_provider
    from app.memory.service import MemoryService

    embedding_provider = get_embedding_provider(get_settings())
    memory_service = MemoryService(db, embedding_provider)

    # Recall handoff memories for this agent
    handoff_memories = await memory_service.recall(
        f"agent={agent_name} blueprint handoff confidence",
        project_id=project_id,
        agent_type=agent_name,
        memory_type="episodic",
        limit=50,
    )

    # Recall outcome memories
    outcome_memories = await memory_service.recall(
        "blueprint outcome",
        project_id=project_id,
        memory_type="episodic",
        limit=50,
    )

    # Build run_id → outcome map
    outcome_map: dict[str, bool] = {}
    for entry, _ in outcome_memories:
        meta: dict[str, Any] = entry.metadata_json or {}
        if meta.get("source") != "blueprint_outcome":
            continue
        run_id = meta.get("run_id", "")
        if run_id:
            outcome_map[run_id] = meta.get("qa_passed", False)

    # Collect confidence + actual outcome pairs
    confidence_values: list[float] = []
    actual_passes: list[bool] = []

    for entry, score in handoff_memories:
        if score < 0.2:
            continue
        meta = entry.metadata_json or {}
        if meta.get("source") != "blueprint_handoff":
            continue
        confidence = meta.get("confidence")
        run_id = meta.get("run_id", "")
        if confidence is None or not run_id:
            continue
        if run_id not in outcome_map:
            continue

        confidence_values.append(float(confidence))
        actual_passes.append(outcome_map[run_id])

    sample_count = len(confidence_values)
    if sample_count < MIN_CALIBRATION_SAMPLES:
        return CalibrationResult(
            agent_name=agent_name,
            discount=DEFAULT_DISCOUNT,
            sample_count=sample_count,
            effective_threshold=_CONFIDENCE_REVIEW_THRESHOLD,
        )

    avg_confidence = sum(confidence_values) / sample_count
    actual_pass_rate = sum(1 for p in actual_passes if p) / sample_count

    # Avoid division by zero
    if avg_confidence <= 0:
        discount = DEFAULT_DISCOUNT
    else:
        discount = min(actual_pass_rate / avg_confidence, 1.5)  # cap at 1.5

    # Clamp discount to reasonable range
    discount = max(0.3, min(discount, 1.5))

    # Effective threshold: if discount < 1, we need higher raw confidence
    effective_threshold = (
        _CONFIDENCE_REVIEW_THRESHOLD / discount if discount > 0 else _CONFIDENCE_REVIEW_THRESHOLD
    )
    # Clamp threshold to [0.1, 0.95]
    effective_threshold = max(0.1, min(effective_threshold, 0.95))

    logger.info(
        "confidence.calibration_computed",
        agent=agent_name,
        discount=round(discount, 3),
        avg_confidence=round(avg_confidence, 3),
        actual_pass_rate=round(actual_pass_rate, 3),
        sample_count=sample_count,
        effective_threshold=round(effective_threshold, 3),
    )

    return CalibrationResult(
        agent_name=agent_name,
        discount=round(discount, 4),
        sample_count=sample_count,
        effective_threshold=round(effective_threshold, 4),
    )


def apply_calibration(raw_confidence: float, calibration: CalibrationResult) -> float:
    """Apply calibration discount to a raw confidence score."""
    return raw_confidence * calibration.discount
