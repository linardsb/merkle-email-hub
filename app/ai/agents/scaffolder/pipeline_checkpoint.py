"""Per-pass checkpointing for the Scaffolder 3-pass pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, runtime_checkable

PassName = Literal["layout", "content_design"]


@dataclass(frozen=True)
class PipelineCheckpoint:
    """Snapshot of completed pass results within a pipeline execution."""

    run_id: str
    pass_name: PassName
    pass_index: int  # 0=layout, 1=content_design
    data: dict[str, Any]  # serialized pass output
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class PipelineCheckpointCallback(Protocol):
    """Callback protocol for persisting pipeline pass checkpoints."""

    async def save_pass(self, checkpoint: PipelineCheckpoint) -> None:
        """Persist a pass checkpoint. Must be fire-and-forget safe."""
        ...

    async def load_passes(self, run_id: str) -> list[PipelineCheckpoint]:
        """Load all pass checkpoints for a pipeline run, ordered by pass_index."""
        ...


def serialize_layout_pass(
    template_name: str,
    reasoning: str,
    section_order: tuple[str, ...],
    fallback_template: str | None,
    section_decisions: tuple[Any, ...],
    slot_details: list[dict[str, object]],
) -> dict[str, Any]:
    """Serialize layout pass output for checkpoint storage."""
    return {
        "template_name": template_name,
        "reasoning": reasoning,
        "section_order": list(section_order),
        "fallback_template": fallback_template,
        "section_decisions": [asdict(sd) for sd in section_decisions],
        "slot_details": slot_details,
    }


def serialize_content_design_pass(
    slot_fills: tuple[Any, ...],
    design_tokens: Any,  # noqa: ANN401
) -> dict[str, Any]:
    """Serialize content + design pass outputs for checkpoint storage."""
    return {
        "slot_fills": [asdict(sf) for sf in slot_fills],
        "design_tokens": asdict(design_tokens),
    }
