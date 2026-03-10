"""Tests for graph context trigger detection and formatting."""

import pytest

from app.ai.blueprints.graph_context import (
    format_graph_context,
    should_fetch_graph_context,
)
from app.knowledge.graph.protocols import (
    GraphEntity,
    GraphRelationship,
    GraphSearchResult,
)


class TestShouldFetchGraphContext:
    """Tests for trigger detection logic."""

    def test_always_true_on_retry(self) -> None:
        assert should_fetch_graph_context("simple brief", iteration=1) is True

    def test_triggers_on_email_client_mention(self) -> None:
        assert should_fetch_graph_context("Make this work in Outlook") is True

    def test_triggers_on_dark_mode(self) -> None:
        assert should_fetch_graph_context("Add dark mode support") is True

    def test_triggers_on_css_support(self) -> None:
        assert should_fetch_graph_context("Check CSS support for flexbox") is True

    def test_triggers_on_accessibility(self) -> None:
        assert should_fetch_graph_context("WCAG AA compliance needed") is True

    def test_triggers_on_mso_conditional(self) -> None:
        assert should_fetch_graph_context("Add MSO conditional comments") is True

    def test_triggers_on_liquid_personalisation(self) -> None:
        assert should_fetch_graph_context("Add Liquid personalisation tags") is True

    def test_no_trigger_on_generic_brief(self) -> None:
        assert should_fetch_graph_context("Create a promotional email") is False

    def test_triggers_on_html_content(self) -> None:
        assert should_fetch_graph_context("Build email", html="<!--[if mso]><v:rect>") is True

    def test_triggers_on_qa_failures(self) -> None:
        assert (
            should_fetch_graph_context("Build email", qa_failures=["dark mode check failed"])
            is True
        )


class TestFormatGraphContext:
    """Tests for graph result formatting."""

    def test_empty_results(self) -> None:
        assert format_graph_context([]) == ""

    def test_content_only_results(self) -> None:
        results = [
            GraphSearchResult(content="Apple Mail supports prefers-color-scheme"),
            GraphSearchResult(content="Outlook ignores color-scheme meta"),
        ]
        formatted = format_graph_context(results)
        assert "GRAPH KNOWLEDGE CONTEXT" in formatted
        assert "Apple Mail supports" in formatted
        assert "Outlook ignores" in formatted

    def test_structured_triplet_results(self) -> None:
        entities = (
            GraphEntity(id="e1", name="Apple Mail", entity_type="email_client"),
            GraphEntity(id="e2", name="prefers-color-scheme", entity_type="css_property"),
        )
        relationships = (
            GraphRelationship(
                source_id="e1",
                target_id="e2",
                relationship_type="supports",
                properties={"since": "macOS Mojave"},
            ),
        )
        results = [GraphSearchResult(content="", entities=entities, relationships=relationships)]
        formatted = format_graph_context(results)
        assert "Apple Mail [supports] prefers-color-scheme" in formatted
        assert "since: macOS Mojave" in formatted

    def test_entity_id_fallback(self) -> None:
        """When entity not found in list, falls back to raw ID."""
        relationships = (
            GraphRelationship(
                source_id="unknown_id",
                target_id="also_unknown",
                relationship_type="breaks_in",
            ),
        )
        results = [GraphSearchResult(content="", entities=(), relationships=relationships)]
        formatted = format_graph_context(results)
        assert "unknown_id [breaks in] also_unknown" in formatted


class TestEngineGraphIntegration:
    """Tests for engine graph context injection (mocked provider)."""

    @pytest.mark.asyncio
    async def test_graph_context_injected_when_triggered(self) -> None:
        """Verify engine injects graph_context metadata when provider returns results."""
        from unittest.mock import AsyncMock, MagicMock

        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
        from app.ai.blueprints.protocols import NodeResult

        mock_node = MagicMock()
        mock_node.name = "test_agent"
        mock_node.node_type = "agentic"
        mock_node.execute = AsyncMock(
            return_value=NodeResult(status="success", html="<html>output</html>")
        )

        mock_graph = AsyncMock()
        mock_graph.search = AsyncMock(
            return_value=[
                GraphSearchResult(content="Outlook needs MSO conditionals for VML"),
            ]
        )

        definition = BlueprintDefinition(
            name="test",
            nodes={"test_agent": mock_node},
            edges=[],
            entry_node="test_agent",
        )

        engine = BlueprintEngine(
            definition,
            graph_provider=mock_graph,
            project_id=1,
        )

        await engine.run(brief="Make this work in Outlook 2019")

        mock_graph.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_graph_context_skipped_when_no_trigger(self) -> None:
        """Verify engine skips graph search when brief has no trigger keywords."""
        from unittest.mock import AsyncMock, MagicMock

        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
        from app.ai.blueprints.protocols import NodeResult

        mock_node = MagicMock()
        mock_node.name = "test_agent"
        mock_node.node_type = "agentic"
        mock_node.execute = AsyncMock(
            return_value=NodeResult(status="success", html="<html>done</html>")
        )

        mock_graph = AsyncMock()

        definition = BlueprintDefinition(
            name="test",
            nodes={"test_agent": mock_node},
            edges=[],
            entry_node="test_agent",
        )

        engine = BlueprintEngine(
            definition,
            graph_provider=mock_graph,
            project_id=1,
        )

        await engine.run(brief="Create a simple promotional email")

        mock_graph.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_graph_search_failure_does_not_crash_pipeline(self) -> None:
        """Verify that graph search errors are swallowed gracefully."""
        from unittest.mock import AsyncMock, MagicMock

        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
        from app.ai.blueprints.protocols import NodeResult

        mock_node = MagicMock()
        mock_node.name = "test_agent"
        mock_node.node_type = "agentic"
        mock_node.execute = AsyncMock(
            return_value=NodeResult(status="success", html="<html>ok</html>")
        )

        mock_graph = AsyncMock()
        mock_graph.search = AsyncMock(side_effect=RuntimeError("Cognee unavailable"))

        definition = BlueprintDefinition(
            name="test",
            nodes={"test_agent": mock_node},
            edges=[],
            entry_node="test_agent",
        )

        engine = BlueprintEngine(
            definition,
            graph_provider=mock_graph,
            project_id=1,
        )

        run = await engine.run(brief="Fix Outlook VML background")
        assert run.status in ("completed", "needs_review")
