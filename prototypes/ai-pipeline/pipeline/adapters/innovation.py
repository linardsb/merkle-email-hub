"""Innovation agent artifact adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.ai.pipeline.adapters import register_adapter
from app.ai.pipeline.artifacts import ArtifactStore, HtmlArtifact


@dataclass(frozen=True)
class InnovationArtifactAdapter:
    """Reads optional HTML, produces HTML with innovative techniques."""

    agent_name: str = "innovation"

    def input_artifacts(self) -> frozenset[str]:
        return frozenset({"html"})

    def output_artifacts(self) -> frozenset[str]:
        return frozenset({"html"})

    def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:
        html_art = store.get_optional("html", HtmlArtifact)
        return {"html": html_art.html if html_art else None}

    def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
        now = datetime.now(UTC)
        html = getattr(response, "html", "") or ""
        if html:
            store.put(
                "html",
                HtmlArtifact(name="html", produced_by="innovation", produced_at=now, html=html),
            )


register_adapter(InnovationArtifactAdapter())
