"""Outlook fixer agent artifact adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.ai.pipeline.adapters import register_adapter
from app.ai.pipeline.artifacts import ArtifactStore, HtmlArtifact, QaResultArtifact


@dataclass(frozen=True)
class OutlookFixerArtifactAdapter:
    """Reads HTML + optional QA results, produces fixed HTML."""

    agent_name: str = "outlook_fixer"

    def input_artifacts(self) -> frozenset[str]:
        return frozenset({"html", "qa_results"})

    def output_artifacts(self) -> frozenset[str]:
        return frozenset({"html"})

    def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:
        html_art = store.get("html", HtmlArtifact)
        qa_art = store.get_optional("qa_results", QaResultArtifact)
        return {
            "html": html_art.html,
            "qa_results": qa_art.results if qa_art else None,
        }

    def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
        now = datetime.now(UTC)
        html = getattr(response, "html", "") or ""
        store.put(
            "html",
            HtmlArtifact(name="html", produced_by="outlook_fixer", produced_at=now, html=html),
        )


register_adapter(OutlookFixerArtifactAdapter())
