"""Tests for AgentHandoff ↔ ArtifactStore bridge methods."""

from __future__ import annotations

from app.ai.blueprints.protocols import AgentHandoff
from app.ai.pipeline.artifacts import ArtifactStore, HtmlArtifact


class TestHandoffBridge:
    def test_handoff_to_artifacts(self) -> None:
        handoff = AgentHandoff(agent_name="scaffolder", artifact="<table>hello</table>")
        store = ArtifactStore()
        handoff.to_artifacts(store)

        assert store.has("html")
        html_art = store.get("html", HtmlArtifact)
        assert html_art.html == "<table>hello</table>"
        assert html_art.produced_by == "scaffolder"

    def test_handoff_to_artifacts_empty(self) -> None:
        handoff = AgentHandoff(agent_name="knowledge", artifact="")
        store = ArtifactStore()
        handoff.to_artifacts(store)
        assert not store.has("html")

    def test_from_artifact_store(self) -> None:
        store = ArtifactStore()
        original = AgentHandoff(agent_name="dark_mode", artifact="<table>dark</table>")
        original.to_artifacts(store)

        restored = AgentHandoff.from_artifact_store(store, "dark_mode")
        assert restored.agent_name == "dark_mode"
        assert restored.artifact == "<table>dark</table>"

    def test_from_artifact_store_empty(self) -> None:
        store = ArtifactStore()
        restored = AgentHandoff.from_artifact_store(store, "test")
        assert restored.artifact == ""
