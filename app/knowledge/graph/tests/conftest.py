"""Test fixtures for graph knowledge tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.knowledge.graph.protocols import GraphSearchResult


def make_graph_search_result(
    *,
    content: str = "Test graph result",
    score: float = 0.85,
) -> GraphSearchResult:
    return GraphSearchResult(content=content, score=score)


def make_mock_graph_provider() -> AsyncMock:
    """Create a mock GraphKnowledgeProvider."""
    mock = AsyncMock()
    mock.add_documents = AsyncMock(return_value=None)
    mock.build_graph = AsyncMock(return_value=None)
    mock.search = AsyncMock(return_value=[make_graph_search_result()])
    mock.search_completion = AsyncMock(return_value="Graph-grounded answer")
    mock.reset = AsyncMock(return_value=None)
    return mock
