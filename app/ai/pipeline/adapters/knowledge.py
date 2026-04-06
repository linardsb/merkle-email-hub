"""Knowledge agent artifact adapter."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.pipeline.adapters import register_adapter
from app.ai.pipeline.artifacts import ArtifactStore


@dataclass(frozen=True)
class KnowledgeArtifactAdapter:
    """Advisory agent — reads nothing, produces nothing."""

    agent_name: str = "knowledge"

    def input_artifacts(self) -> frozenset[str]:
        return frozenset()

    def output_artifacts(self) -> frozenset[str]:
        return frozenset()

    def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:  # noqa: ARG002
        return {}

    def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
        pass


register_adapter(KnowledgeArtifactAdapter())
