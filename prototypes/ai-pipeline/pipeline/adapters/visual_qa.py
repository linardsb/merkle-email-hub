"""Visual QA agent artifact adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.ai.pipeline.adapters import register_adapter
from app.ai.pipeline.artifacts import (
    ArtifactStore,
    CorrectionArtifact,
    HtmlArtifact,
    ScreenshotArtifact,
)


@dataclass(frozen=True)
class VisualQAArtifactAdapter:
    """Reads HTML + optional screenshots, produces corrections + HTML."""

    agent_name: str = "visual_qa"

    def input_artifacts(self) -> frozenset[str]:
        return frozenset({"html", "screenshots"})

    def output_artifacts(self) -> frozenset[str]:
        return frozenset({"corrections", "html"})

    def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:
        html_art = store.get("html", HtmlArtifact)
        screenshots_art = store.get_optional("screenshots", ScreenshotArtifact)
        return {
            "html": html_art.html,
            "screenshots": screenshots_art.screenshots if screenshots_art else None,
        }

    def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
        now = datetime.now(UTC)
        corrections = tuple(getattr(response, "corrections", ()) or ())
        applied = getattr(response, "applied", 0)
        skipped = getattr(response, "skipped", 0)
        if corrections:
            store.put(
                "corrections",
                CorrectionArtifact(
                    name="corrections",
                    produced_by="visual_qa",
                    produced_at=now,
                    corrections=corrections,
                    applied=applied,
                    skipped=skipped,
                ),
            )
        html = getattr(response, "html", "") or ""
        if html:
            store.put(
                "html",
                HtmlArtifact(name="html", produced_by="visual_qa", produced_at=now, html=html),
            )


register_adapter(VisualQAArtifactAdapter())
