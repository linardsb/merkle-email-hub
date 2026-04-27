"""Tests for built-in hooks."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.hooks.builtin import cost_tracker, progress_reporter
from app.ai.hooks.registry import HookContext, HookEvent
from app.ai.pipeline.artifacts import ArtifactStore, HtmlArtifact
from app.core.exceptions import HookAbortError
from app.core.progress import ProgressTracker


def _make_context(
    event: HookEvent,
    run_id: str = "test-run",
    agent_name: str | None = None,
    cost_tokens: int = 0,
    metadata: dict[str, Any] | None = None,
) -> HookContext:
    return HookContext(
        run_id=run_id,
        pipeline_name="test-pipeline",
        event=event,
        agent_name=agent_name,
        cost_tokens=cost_tokens,
        metadata=metadata or {},
    )


class TestCostTracker:
    @pytest.fixture(autouse=True)
    def _clear_totals(self) -> Iterator[None]:
        cost_tracker._run_totals.clear()
        cost_tracker._run_timestamps.clear()
        yield
        cost_tracker._run_totals.clear()
        cost_tracker._run_timestamps.clear()

    @pytest.mark.asyncio
    async def test_cost_tracker_accumulates(self) -> None:
        # 3 agents with different token counts
        for agent, tokens in [("agent_a", 100), ("agent_b", 200), ("agent_a", 50)]:
            ctx = _make_context(
                HookEvent.POST_AGENT,
                agent_name=agent,
                cost_tokens=tokens,
            )
            await cost_tracker._on_post_agent(ctx)

        # Verify accumulation
        totals = cost_tracker._run_totals["test-run"]
        assert totals["agent_a"] == 150
        assert totals["agent_b"] == 200

        # Summary cleans up
        summary_ctx = _make_context(HookEvent.POST_PIPELINE)
        result = await cost_tracker._on_post_pipeline(summary_ctx)
        assert result["total_tokens"] == 350
        assert "test-run" not in cost_tracker._run_totals


class TestAdversarialGate:
    @pytest.mark.asyncio
    async def test_adversarial_gate_reject_aborts(self) -> None:
        from app.ai.hooks.builtin import adversarial_gate

        # Mock EvalVerdict nested inside EvaluatorResponse
        mock_eval_verdict = AsyncMock()
        mock_eval_verdict.verdict = "reject"
        mock_eval_verdict.feedback = "Output contains unsafe patterns"
        mock_eval_verdict.score = 0.2

        mock_response = AsyncMock()
        mock_response.verdict = mock_eval_verdict

        mock_evaluator = AsyncMock()
        mock_evaluator.evaluate = AsyncMock(return_value=mock_response)

        store = ArtifactStore()
        store.put(
            "html",
            HtmlArtifact(
                name="html",
                produced_by="scaffolder",
                produced_at=datetime.now(UTC),
                html="<table><tr><td>test</td></tr></table>",
            ),
        )
        ctx = HookContext(
            run_id="test-run",
            pipeline_name="test-pipeline",
            event=HookEvent.POST_AGENT,
            agent_name="scaffolder",
            artifacts=store,
        )

        with (
            patch(
                "app.ai.agents.evaluator.service.EvaluatorAgentService",
                return_value=mock_evaluator,
            ),
            patch(
                "app.core.config.get_settings",
            ) as mock_settings,
        ):
            mock_settings.return_value.ai.evaluator.enabled = True

            with pytest.raises(HookAbortError, match="rejected"):
                await adversarial_gate._on_post_agent(ctx)


class TestProgressReporter:
    @pytest.fixture(autouse=True)
    def _clear_progress(self) -> Iterator[None]:
        yield
        ProgressTracker.clear()

    @pytest.mark.asyncio
    async def test_progress_reporter_updates(self) -> None:
        # PRE_PIPELINE: start tracking
        ctx = _make_context(HookEvent.PRE_PIPELINE)
        await progress_reporter._on_pre_pipeline(ctx)

        entry = ProgressTracker.get("test-run")
        assert entry is not None
        assert entry.operation_type == "pipeline"

        # POST_LEVEL: update progress (level 1 of 3)
        ctx = HookContext(
            run_id="test-run",
            pipeline_name="test-pipeline",
            event=HookEvent.POST_LEVEL,
            level=0,
            metadata={"total_levels": 3},
        )
        await progress_reporter._on_post_level(ctx)

        entry = ProgressTracker.get("test-run")
        assert entry is not None
        assert entry.progress == 33

        # POST_PIPELINE: complete
        ctx = _make_context(
            HookEvent.POST_PIPELINE,
            metadata={"traces": []},
        )
        await progress_reporter._on_post_pipeline(ctx)

        entry = ProgressTracker.get("test-run")
        assert entry is not None
        assert entry.progress == 100
        assert entry.status.value == "completed"
