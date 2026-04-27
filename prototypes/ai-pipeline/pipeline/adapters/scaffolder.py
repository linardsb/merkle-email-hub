"""Scaffolder agent artifact adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.ai.pipeline.adapters import register_adapter
from app.ai.pipeline.artifacts import (
    ArtifactStore,
    BuildPlanArtifact,
    DesignTokenArtifact,
    HtmlArtifact,
)


@dataclass(frozen=True)
class ScaffolderArtifactAdapter:
    """Maps design tokens input to HTML + build plan output."""

    agent_name: str = "scaffolder"

    def input_artifacts(self) -> frozenset[str]:
        return frozenset({"design_tokens"})

    def output_artifacts(self) -> frozenset[str]:
        return frozenset({"html", "build_plan"})

    def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:
        tokens = store.get_optional("design_tokens", DesignTokenArtifact)
        return {"design_tokens": tokens.tokens if tokens else None}

    def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
        now = datetime.now(UTC)
        html = getattr(response, "html", "") or ""
        store.put(
            "html",
            HtmlArtifact(name="html", produced_by="scaffolder", produced_at=now, html=html),
        )
        plan = getattr(response, "plan", None)
        if plan is not None:
            store.put(
                "build_plan",
                BuildPlanArtifact(
                    name="build_plan", produced_by="scaffolder", produced_at=now, plan=plan
                ),
            )


register_adapter(ScaffolderArtifactAdapter())
