"""Code reviewer agent artifact adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.ai.pipeline.adapters import register_adapter
from app.ai.pipeline.artifacts import ArtifactStore, HtmlArtifact, QaResultArtifact


@dataclass(frozen=True)
class CodeReviewerArtifactAdapter:
    """Reads HTML, produces QA results."""

    agent_name: str = "code_reviewer"

    def input_artifacts(self) -> frozenset[str]:
        return frozenset({"html"})

    def output_artifacts(self) -> frozenset[str]:
        return frozenset({"qa_results"})

    def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:
        html_art = store.get("html", HtmlArtifact)
        return {"html": html_art.html}

    def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
        now = datetime.now(UTC)
        results = tuple(getattr(response, "results", ()) or ())
        passed = getattr(response, "passed", True)
        score = getattr(response, "score", 1.0)
        store.put(
            "qa_results",
            QaResultArtifact(
                name="qa_results",
                produced_by="code_reviewer",
                produced_at=now,
                results=results,
                passed=passed,
                score=score,
            ),
        )


register_adapter(CodeReviewerArtifactAdapter())
