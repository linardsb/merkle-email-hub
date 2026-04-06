"""Artifact adapters for per-agent input/output mapping."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.ai.pipeline.artifacts import ArtifactStore

__all__ = [
    "ADAPTER_REGISTRY",
    "ArtifactAdapter",
    "register_adapter",
]


@runtime_checkable
class ArtifactAdapter(Protocol):
    """Contract for converting between artifacts and agent I/O."""

    @property
    def agent_name(self) -> str:
        """Agent name this adapter handles."""
        ...

    def input_artifacts(self) -> frozenset[str]:
        """Artifact names this agent reads."""
        ...

    def output_artifacts(self) -> frozenset[str]:
        """Artifact names this agent produces."""
        ...

    def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:
        """Convert artifacts to agent kwargs."""
        ...

    def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
        """Write agent outputs to artifacts in the store."""
        ...


ADAPTER_REGISTRY: dict[str, ArtifactAdapter] = {}


def register_adapter(adapter: ArtifactAdapter) -> ArtifactAdapter:
    """Register an adapter in the global registry."""
    ADAPTER_REGISTRY[adapter.agent_name] = adapter
    return adapter
