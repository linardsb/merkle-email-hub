"""Tests for knowledge graph pre-query service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agents.knowledge_prefetch import (
    PrefetchResult,
    _cache_key,
    build_prefetch_query,
    format_prefetch_context,
    prefetch_prior_outcomes,
)
from app.knowledge.graph.protocols import GraphSearchResult


class TestBuildPrefetchQuery:
    def test_with_project_id(self) -> None:
        q = build_prefetch_query("scaffolder", "Build a newsletter", 42)
        assert "agent:scaffolder" in q
        assert "task:Build a newsletter" in q
        assert "project:42" in q

    def test_without_project_id(self) -> None:
        q = build_prefetch_query("dark_mode", "Add dark mode", None)
        assert "agent:dark_mode" in q
        assert "project:" not in q

    def test_brief_truncated(self) -> None:
        long_brief = "x" * 1000
        q = build_prefetch_query("scaffolder", long_brief, 1)
        # Brief should be capped at 500 chars
        assert len(q.split("task:")[1].split(" project:")[0]) == 500


class TestPrefetchPriorOutcomes:
    @pytest.mark.asyncio
    async def test_returns_results_above_threshold(self) -> None:
        mock_provider = AsyncMock()
        mock_provider.search.return_value = [
            GraphSearchResult(content="Prior newsletter layout", score=0.8),
            GraphSearchResult(content="Unrelated result", score=0.1),
            GraphSearchResult(content="Another match", score=0.5),
        ]

        with (
            patch("app.ai.agents.knowledge_prefetch._get_cached", return_value=None),
            patch(
                "app.ai.agents.knowledge_prefetch._set_cached",
                new_callable=AsyncMock,
            ),
        ):
            results = await prefetch_prior_outcomes(
                agent_name="scaffolder",
                brief="Build a newsletter",
                project_id=42,
                graph_provider=mock_provider,
                min_score=0.3,
            )

        assert len(results) == 2
        assert results[0].score == 0.8
        assert results[1].score == 0.5

    @pytest.mark.asyncio
    async def test_returns_cached_results(self) -> None:
        cached = [PrefetchResult(summary="Cached result", agent_type="scaffolder", score=0.9)]

        with patch("app.ai.agents.knowledge_prefetch._get_cached", return_value=cached):
            results = await prefetch_prior_outcomes(
                agent_name="scaffolder",
                brief="Build a newsletter",
                project_id=42,
                graph_provider=AsyncMock(),
            )

        assert len(results) == 1
        assert results[0].summary == "Cached result"

    @pytest.mark.asyncio
    async def test_graph_error_returns_empty(self) -> None:
        mock_provider = AsyncMock()
        mock_provider.search.side_effect = RuntimeError("Cognee down")

        with patch("app.ai.agents.knowledge_prefetch._get_cached", return_value=None):
            results = await prefetch_prior_outcomes(
                agent_name="scaffolder",
                brief="Build a newsletter",
                project_id=42,
                graph_provider=mock_provider,
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_respects_top_k(self) -> None:
        mock_provider = AsyncMock()
        mock_provider.search.return_value = [
            GraphSearchResult(content=f"Result {i}", score=0.9 - i * 0.1) for i in range(5)
        ]

        with (
            patch("app.ai.agents.knowledge_prefetch._get_cached", return_value=None),
            patch(
                "app.ai.agents.knowledge_prefetch._set_cached",
                new_callable=AsyncMock,
            ),
        ):
            results = await prefetch_prior_outcomes(
                agent_name="scaffolder",
                brief="test",
                project_id=1,
                graph_provider=mock_provider,
                top_k=2,
            )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_caps_summary_length(self) -> None:
        mock_provider = AsyncMock()
        mock_provider.search.return_value = [
            GraphSearchResult(content="x" * 2000, score=0.9),
        ]

        with (
            patch("app.ai.agents.knowledge_prefetch._get_cached", return_value=None),
            patch(
                "app.ai.agents.knowledge_prefetch._set_cached",
                new_callable=AsyncMock,
            ),
        ):
            results = await prefetch_prior_outcomes(
                agent_name="scaffolder",
                brief="test",
                project_id=1,
                graph_provider=mock_provider,
            )

        assert len(results[0].summary) == 1000


class TestFormatPrefetchContext:
    def test_empty_results(self) -> None:
        assert format_prefetch_context([]) == ""

    def test_formats_results(self) -> None:
        results = [
            PrefetchResult(
                summary="Built a 3-column layout",
                agent_type="scaffolder",
                score=0.85,
            ),
            PrefetchResult(
                summary="Hero + CTA pattern",
                agent_type="scaffolder",
                score=0.72,
            ),
        ]
        output = format_prefetch_context(results)
        assert "Prior Work Reference" in output
        assert "Advisory" in output
        assert "0.85" in output
        assert "3-column layout" in output
        assert "Reference 1" in output
        assert "Reference 2" in output

    def test_includes_adapt_not_copy_instruction(self) -> None:
        results = [PrefetchResult(summary="test", agent_type="scaffolder", score=0.9)]
        output = format_prefetch_context(results)
        assert "adapt" in output.lower()


class TestCacheKeyIsolation:
    def test_different_projects_different_keys(self) -> None:
        k1 = _cache_key("scaffolder", "abc123", 1)
        k2 = _cache_key("scaffolder", "abc123", 2)
        assert k1 != k2

    def test_none_project_uses_global(self) -> None:
        k = _cache_key("scaffolder", "abc123", None)
        assert "global" in k

    def test_different_agents_different_keys(self) -> None:
        k1 = _cache_key("scaffolder", "abc123", 1)
        k2 = _cache_key("dark_mode", "abc123", 1)
        assert k1 != k2
