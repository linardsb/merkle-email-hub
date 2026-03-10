# pyright: reportReturnType=false, reportArgumentType=false
"""Tests for the OutcomeGraphPoller — Redis drain and Cognee ingestion."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.blueprints.outcome_poller import BATCH_SIZE, OutcomeGraphPoller


@pytest.fixture()
def poller() -> OutcomeGraphPoller:
    return OutcomeGraphPoller()


class TestFetch:
    @pytest.mark.asyncio()
    async def test_drains_queue(self, poller: OutcomeGraphPoller) -> None:
        items = [json.dumps({"outcome_text": f"outcome {i}", "project_id": 1}) for i in range(3)]
        mock_redis = AsyncMock()
        mock_redis.lpop = AsyncMock(side_effect=[*items, None])

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await poller.fetch()

        assert len(result) == 3

    @pytest.mark.asyncio()
    async def test_empty_queue(self, poller: OutcomeGraphPoller) -> None:
        mock_redis = AsyncMock()
        mock_redis.lpop = AsyncMock(return_value=None)

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await poller.fetch()

        assert result == []

    @pytest.mark.asyncio()
    async def test_respects_batch_size(self, poller: OutcomeGraphPoller) -> None:
        items = [
            json.dumps({"outcome_text": f"outcome {i}", "project_id": 1})
            for i in range(BATCH_SIZE + 5)
        ]
        mock_redis = AsyncMock()
        # Return BATCH_SIZE items then stop (lpop called BATCH_SIZE times)
        mock_redis.lpop = AsyncMock(side_effect=items[:BATCH_SIZE])

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await poller.fetch()

        assert len(result) == BATCH_SIZE

    @pytest.mark.asyncio()
    async def test_skips_invalid_json(self, poller: OutcomeGraphPoller) -> None:
        mock_redis = AsyncMock()
        mock_redis.lpop = AsyncMock(
            side_effect=[
                json.dumps({"outcome_text": "valid", "project_id": 1}),
                "not-valid-json{{{",
                json.dumps({"outcome_text": "also valid", "project_id": 2}),
                None,
            ]
        )

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await poller.fetch()

        assert len(result) == 2
        assert result[0]["outcome_text"] == "valid"
        assert result[1]["outcome_text"] == "also valid"


class TestStore:
    @pytest.mark.asyncio()
    async def test_groups_by_project(self, poller: OutcomeGraphPoller) -> None:
        mock_provider = MagicMock()
        mock_provider.add_documents = AsyncMock()

        outcomes = [
            {"outcome_text": "outcome A", "project_id": 1},
            {"outcome_text": "outcome B", "project_id": 2},
            {"outcome_text": "outcome C", "project_id": 1},
        ]

        with patch(
            "app.knowledge.graph.cognee_provider.CogneeGraphProvider",
            return_value=mock_provider,
        ):
            await poller.store(outcomes)

        assert mock_provider.add_documents.await_count == 2
        calls = mock_provider.add_documents.call_args_list
        call_datasets = {c.kwargs["dataset_name"] for c in calls}
        assert call_datasets == {"project_1", "project_2"}

    @pytest.mark.asyncio()
    async def test_empty_outcomes_noop(self, poller: OutcomeGraphPoller) -> None:
        # Should return immediately without importing CogneeGraphProvider
        await poller.store([])

    @pytest.mark.asyncio()
    async def test_cognee_unavailable(self, poller: OutcomeGraphPoller) -> None:
        outcomes = [{"outcome_text": "outcome A", "project_id": 1}]

        with patch(
            "app.knowledge.graph.cognee_provider.CogneeGraphProvider",
            side_effect=ImportError("cognee not installed"),
        ):
            # Should not raise
            await poller.store(outcomes)

    @pytest.mark.asyncio()
    async def test_global_dataset_for_none_project(self, poller: OutcomeGraphPoller) -> None:
        mock_provider = MagicMock()
        mock_provider.add_documents = AsyncMock()

        outcomes = [{"outcome_text": "global outcome", "project_id": None}]

        with patch(
            "app.knowledge.graph.cognee_provider.CogneeGraphProvider",
            return_value=mock_provider,
        ):
            await poller.store(outcomes)

        mock_provider.add_documents.assert_awaited_once_with(
            ["global outcome"],
            dataset_name="global",
        )
