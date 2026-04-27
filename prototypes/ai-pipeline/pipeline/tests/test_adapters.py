"""Tests for per-agent artifact adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

# Force adapter registration by importing all adapter modules
import app.ai.pipeline.adapters.accessibility  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.code_reviewer  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.content  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.dark_mode  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.innovation  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.knowledge  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.outlook_fixer  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.personalisation  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.scaffolder  # pyright: ignore[reportUnusedImport]
import app.ai.pipeline.adapters.visual_qa  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.ai.pipeline.adapters import ADAPTER_REGISTRY, ArtifactAdapter
from app.ai.pipeline.artifacts import ArtifactStore, HtmlArtifact

NOW = datetime(2026, 1, 1, tzinfo=UTC)

EXPECTED_AGENTS = frozenset(
    {
        "scaffolder",
        "dark_mode",
        "content",
        "outlook_fixer",
        "accessibility",
        "personalisation",
        "code_reviewer",
        "knowledge",
        "innovation",
        "visual_qa",
    }
)


class TestAdapterRegistry:
    def test_registry_populated(self) -> None:
        registered = frozenset(ADAPTER_REGISTRY.keys())
        assert EXPECTED_AGENTS <= registered

    def test_adapter_protocol_compliance(self) -> None:
        for name, adapter in ADAPTER_REGISTRY.items():
            assert isinstance(adapter, ArtifactAdapter), f"{name} does not satisfy ArtifactAdapter"


class TestScaffolderAdapter:
    def test_roundtrip(self) -> None:
        adapter = ADAPTER_REGISTRY["scaffolder"]
        store = ArtifactStore()

        # Simulate scaffolder response
        response = SimpleNamespace(html="<table>scaffolded</table>", plan=None)
        adapter.adapt_outputs(response, store)

        assert store.has("html")
        html_art = store.get("html", HtmlArtifact)
        assert html_art.html == "<table>scaffolded</table>"
        assert html_art.produced_by == "scaffolder"

        # Read back via adapt_inputs (for downstream agent)
        dark_adapter = ADAPTER_REGISTRY["dark_mode"]
        inputs = dark_adapter.adapt_inputs(store)
        assert inputs["html"] == "<table>scaffolded</table>"


class TestCodeReviewerAdapter:
    def test_reads_html(self) -> None:
        store = ArtifactStore()
        store.put(
            "html",
            HtmlArtifact(
                name="html", produced_by="test", produced_at=NOW, html="<table>review me</table>"
            ),
        )
        adapter = ADAPTER_REGISTRY["code_reviewer"]
        inputs = adapter.adapt_inputs(store)
        assert inputs["html"] == "<table>review me</table>"
