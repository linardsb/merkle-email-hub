"""Tests for per-agent confidence calibration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.confidence_calibration import (
    DEFAULT_DISCOUNT,
    MIN_CALIBRATION_SAMPLES,
    CalibrationResult,
    apply_calibration,
    compute_calibration,
)


def test_apply_calibration_default() -> None:
    """Default discount (1.0) doesn't change confidence."""
    cal = CalibrationResult(
        agent_name="scaffolder",
        discount=1.0,
        sample_count=0,
        effective_threshold=0.5,
    )
    assert apply_calibration(0.8, cal) == 0.8


def test_apply_calibration_discounted() -> None:
    """Discount < 1.0 reduces confidence."""
    cal = CalibrationResult(
        agent_name="scaffolder",
        discount=0.5,
        sample_count=20,
        effective_threshold=1.0,
    )
    assert apply_calibration(0.8, cal) == pytest.approx(0.4)  # pyright: ignore[reportUnknownMemberType]


@pytest.mark.asyncio
async def test_compute_calibration_no_data() -> None:
    """No handoff memories → default discount."""
    mock_memory_svc = AsyncMock()
    mock_memory_svc.recall = AsyncMock(return_value=[])

    mock_db = AsyncMock()

    with (
        patch("app.knowledge.embedding.get_embedding_provider"),
        patch("app.memory.service.MemoryService", return_value=mock_memory_svc),
    ):
        result = await compute_calibration("scaffolder", None, mock_db)

    assert result.discount == DEFAULT_DISCOUNT
    assert result.sample_count < MIN_CALIBRATION_SAMPLES


@pytest.mark.asyncio
async def test_compute_calibration_overconfident_agent() -> None:
    """Agent reports 0.9 confidence but only 50% pass → discount < 1.0."""
    # Build handoff memories: 12 entries, all with confidence 0.9
    handoff_entries: list[tuple[MagicMock, float]] = []
    for i in range(12):
        entry = MagicMock()
        entry.metadata_json = {
            "source": "blueprint_handoff",
            "confidence": 0.9,
            "run_id": f"run_{i}",
        }
        entry.content = f"handoff {i}"
        handoff_entries.append((entry, 0.8))

    # Build outcome memories: 6 passed, 6 failed
    outcome_entries: list[tuple[MagicMock, float]] = []
    for i in range(12):
        entry = MagicMock()
        entry.metadata_json = {
            "source": "blueprint_outcome",
            "run_id": f"run_{i}",
            "qa_passed": i < 6,  # 50% pass rate
        }
        entry.content = f"outcome {i}"
        outcome_entries.append((entry, 0.8))

    mock_memory_svc = AsyncMock()

    call_count = 0

    async def mock_recall(
        query: str,
        *,
        project_id: int | None = None,
        agent_type: str | None = None,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[tuple[MagicMock, float]]:
        nonlocal call_count
        call_count += 1
        # First call: handoff memories, second call: outcome memories
        if call_count == 1:
            return handoff_entries
        return outcome_entries

    mock_memory_svc.recall = AsyncMock(side_effect=mock_recall)

    mock_db = AsyncMock()

    with (
        patch("app.knowledge.embedding.get_embedding_provider"),
        patch("app.memory.service.MemoryService", return_value=mock_memory_svc),
    ):
        result = await compute_calibration("scaffolder", None, mock_db)

    assert result.sample_count == 12
    # discount = actual_pass_rate / avg_confidence = 0.5 / 0.9 ≈ 0.556
    assert result.discount < 1.0
    assert result.discount == pytest.approx(0.5 / 0.9, abs=0.01)  # pyright: ignore[reportUnknownMemberType]
    # effective_threshold should be higher than base 0.5
    assert result.effective_threshold > 0.5


@pytest.mark.asyncio
async def test_compute_calibration_well_calibrated() -> None:
    """Agent with matching confidence and pass rate → discount ~1.0."""
    handoff_entries: list[tuple[MagicMock, float]] = []
    for i in range(12):
        entry = MagicMock()
        entry.metadata_json = {
            "source": "blueprint_handoff",
            "confidence": 0.8,
            "run_id": f"run_{i}",
        }
        entry.content = f"handoff {i}"
        handoff_entries.append((entry, 0.8))

    outcome_entries: list[tuple[MagicMock, float]] = []
    for i in range(12):
        entry = MagicMock()
        entry.metadata_json = {
            "source": "blueprint_outcome",
            "run_id": f"run_{i}",
            "qa_passed": i < 10,  # 83% pass rate, close to 0.8 confidence
        }
        entry.content = f"outcome {i}"
        outcome_entries.append((entry, 0.8))

    mock_memory_svc = AsyncMock()
    call_count = 0

    async def mock_recall(*args: object, **kwargs: object) -> list[tuple[MagicMock, float]]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return handoff_entries
        return outcome_entries

    mock_memory_svc.recall = AsyncMock(side_effect=mock_recall)

    mock_db = AsyncMock()

    with (
        patch("app.knowledge.embedding.get_embedding_provider"),
        patch("app.memory.service.MemoryService", return_value=mock_memory_svc),
    ):
        result = await compute_calibration("scaffolder", None, mock_db)

    # 83% / 80% ≈ 1.04, capped to 1.04
    assert result.discount >= 0.9
    assert result.effective_threshold <= 0.6  # near base threshold
