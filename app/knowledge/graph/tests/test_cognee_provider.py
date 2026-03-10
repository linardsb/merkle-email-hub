# pyright: reportArgumentType=false
"""Unit tests for CogneeGraphProvider (all Cognee calls mocked)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.knowledge.graph.cognee_provider import CogneeGraphProvider
from app.knowledge.graph.exceptions import (
    GraphNotEnabledError,
    GraphSearchError,
)
from app.knowledge.graph.protocols import GraphSearchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(
    *, enabled: bool = True, llm_provider: str = "", llm_api_key: str = ""
) -> SimpleNamespace:
    """Build a minimal Settings-like object for testing."""
    cognee_cfg = SimpleNamespace(
        enabled=enabled,
        llm_provider=llm_provider,
        llm_model="",
        llm_api_key=llm_api_key,
        graph_db_provider="kuzu",
        neo4j_url="",
        neo4j_user="",
        neo4j_password="",
        vector_db_provider="pgvector",
        chunk_size=512,
        chunk_overlap=50,
        data_directory="data/cognee",
        system_directory="data/cognee/system",
        background_cognify=True,
    )
    ai_cfg = SimpleNamespace(provider="anthropic", model="claude-sonnet-4-6", api_key="sk-test")
    db_cfg = SimpleNamespace(url="postgresql+asyncpg://localhost/test")
    return SimpleNamespace(cognee=cognee_cfg, ai=ai_cfg, database=db_cfg)


@pytest.fixture(autouse=True)
def _reset_config_flag():
    """Reset the module-level config flag between tests."""
    import app.knowledge.graph.cognee_provider as mod

    mod._config_applied = False
    yield
    mod._config_applied = False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_provider_raises_if_disabled():
    settings = _make_settings(enabled=False)
    with pytest.raises(GraphNotEnabledError, match="disabled"):
        CogneeGraphProvider(settings)


@pytest.mark.asyncio
async def test_add_documents_calls_cognee_add():
    settings = _make_settings()
    provider = CogneeGraphProvider(settings)

    mock_cognee = MagicMock()
    mock_cognee.add = AsyncMock(return_value=None)
    mock_cognee.config = MagicMock()

    with patch.dict("sys.modules", {"cognee": mock_cognee}):
        with patch("app.knowledge.graph.config.apply_cognee_config"):
            await provider.add_documents(["doc1", "doc2"], dataset_name="test_ds")

    mock_cognee.add.assert_awaited_once_with(["doc1", "doc2"], dataset_name="test_ds")


@pytest.mark.asyncio
async def test_build_graph_calls_cognify():
    settings = _make_settings()
    provider = CogneeGraphProvider(settings)

    mock_cognee = MagicMock()
    mock_cognee.cognify = AsyncMock(return_value=None)
    mock_cognee.config = MagicMock()

    with patch.dict("sys.modules", {"cognee": mock_cognee}):
        with patch("app.knowledge.graph.config.apply_cognee_config"):
            await provider.build_graph(dataset_name="ds1", background=True)

    mock_cognee.cognify.assert_awaited_once()
    call_kwargs = mock_cognee.cognify.call_args[1]
    assert call_kwargs["datasets"] == ["ds1"]
    assert call_kwargs["run_in_background"] is True


@pytest.mark.asyncio
async def test_search_returns_results():
    settings = _make_settings()
    provider = CogneeGraphProvider(settings)

    mock_search_type = MagicMock()
    mock_search_type.CHUNKS = "CHUNKS"
    mock_search_module = MagicMock()
    mock_search_module.SearchType = mock_search_type

    mock_cognee = MagicMock()
    mock_cognee.search = AsyncMock(return_value=["result1", "result2"])
    mock_cognee.config = MagicMock()
    mock_cognee.api = MagicMock()
    mock_cognee.api.v1 = MagicMock()
    mock_cognee.api.v1.search = mock_search_module

    with patch.dict(
        "sys.modules",
        {
            "cognee": mock_cognee,
            "cognee.api": mock_cognee.api,
            "cognee.api.v1": mock_cognee.api.v1,
            "cognee.api.v1.search": mock_search_module,
        },
    ):
        with patch("app.knowledge.graph.config.apply_cognee_config"):
            results = await provider.search("test query", top_k=5)

    assert len(results) == 2
    assert all(isinstance(r, GraphSearchResult) for r in results)
    assert results[0].content == "result1"


@pytest.mark.asyncio
async def test_search_completion_returns_answer():
    settings = _make_settings()
    provider = CogneeGraphProvider(settings)

    mock_search_type = MagicMock()
    mock_search_type.GRAPH_COMPLETION = "GRAPH_COMPLETION"
    mock_search_module = MagicMock()
    mock_search_module.SearchType = mock_search_type

    mock_cognee = MagicMock()
    mock_cognee.search = AsyncMock(return_value=["The answer is 42"])
    mock_cognee.config = MagicMock()
    mock_cognee.api = MagicMock()
    mock_cognee.api.v1 = MagicMock()
    mock_cognee.api.v1.search = mock_search_module

    with patch.dict(
        "sys.modules",
        {
            "cognee": mock_cognee,
            "cognee.api": mock_cognee.api,
            "cognee.api.v1": mock_cognee.api.v1,
            "cognee.api.v1.search": mock_search_module,
        },
    ):
        with patch("app.knowledge.graph.config.apply_cognee_config"):
            answer = await provider.search_completion("What is the meaning?")

    assert answer == "The answer is 42"


@pytest.mark.asyncio
async def test_search_handles_cognee_error():
    settings = _make_settings()
    provider = CogneeGraphProvider(settings)

    mock_search_type = MagicMock()
    mock_search_type.CHUNKS = "CHUNKS"
    mock_search_module = MagicMock()
    mock_search_module.SearchType = mock_search_type

    mock_cognee = MagicMock()
    mock_cognee.search = AsyncMock(side_effect=RuntimeError("Cognee broke"))
    mock_cognee.config = MagicMock()
    mock_cognee.api = MagicMock()
    mock_cognee.api.v1 = MagicMock()
    mock_cognee.api.v1.search = mock_search_module

    with patch.dict(
        "sys.modules",
        {
            "cognee": mock_cognee,
            "cognee.api": mock_cognee.api,
            "cognee.api.v1": mock_cognee.api.v1,
            "cognee.api.v1.search": mock_search_module,
        },
    ):
        with patch("app.knowledge.graph.config.apply_cognee_config"):
            with pytest.raises(GraphSearchError, match="Cognee broke"):
                await provider.search("fail query")


@pytest.mark.asyncio
async def test_config_applied_once():
    settings = _make_settings()
    provider = CogneeGraphProvider(settings)

    mock_cognee = MagicMock()
    mock_cognee.add = AsyncMock(return_value=None)
    mock_cognee.config = MagicMock()

    with patch.dict("sys.modules", {"cognee": mock_cognee}):
        with patch("app.knowledge.graph.config.apply_cognee_config") as mock_apply:
            await provider.add_documents(["a"])
            await provider.add_documents(["b"])

    # Config should only be applied once despite two operations
    mock_apply.assert_called_once_with(settings)


@pytest.mark.asyncio
async def test_config_inherits_ai_settings():
    settings = _make_settings(llm_provider="", llm_api_key="")

    mock_cognee = MagicMock()
    mock_cognee.add = AsyncMock(return_value=None)
    mock_cognee.config = MagicMock()

    with patch.dict("sys.modules", {"cognee": mock_cognee}):
        # Call apply_cognee_config directly to verify AI setting inheritance
        from app.knowledge.graph.config import apply_cognee_config

        apply_cognee_config(settings)

    # Verify LLM config was set with AI fallback values
    mock_cognee.config.set_llm_config.assert_called_once_with(
        {
            "llm_provider": "anthropic",  # inherited from ai.provider
            "llm_model": "claude-sonnet-4-6",  # inherited from ai.model
            "llm_api_key": "sk-test",  # inherited from ai.api_key
        }
    )
