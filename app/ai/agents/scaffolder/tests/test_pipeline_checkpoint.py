"""Tests for per-pass pipeline checkpointing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.scaffolder.pipeline_checkpoint import (
    PipelineCheckpoint,
    serialize_content_design_pass,
    serialize_layout_pass,
)
from app.ai.agents.schemas.build_plan import (
    DesignTokens,
    SectionDecision,
    SlotFill,
)


class TestSerializeLayoutPass:
    def test_serializes_all_fields(self) -> None:
        data = serialize_layout_pass(
            template_name="newsletter_1col",
            reasoning="Best fit for single-column content",
            section_order=("header", "body", "footer"),
            fallback_template="basic_1col",
            section_decisions=(SectionDecision(section_name="header", background_color="#ffffff"),),
            slot_details=[
                {"slot_id": "headline", "slot_type": "text", "max_chars": 100, "required": True}
            ],
        )
        assert data["template_name"] == "newsletter_1col"
        assert data["section_order"] == ["header", "body", "footer"]
        assert data["fallback_template"] == "basic_1col"
        assert len(data["section_decisions"]) == 1
        assert data["slot_details"][0]["slot_id"] == "headline"

    def test_handles_empty_sections(self) -> None:
        data = serialize_layout_pass("t", "r", (), None, (), [])
        assert data["section_decisions"] == []
        assert data["slot_details"] == []


class TestSerializeContentDesignPass:
    def test_serializes_fills_and_tokens(self) -> None:
        fills = (SlotFill(slot_id="headline", content="Hello"),)
        tokens = DesignTokens(colors={"primary": "#ff0000"})
        data = serialize_content_design_pass(fills, tokens)
        assert len(data["slot_fills"]) == 1
        assert data["slot_fills"][0]["slot_id"] == "headline"
        assert data["design_tokens"]["colors"]["primary"] == "#ff0000"


class TestPipelineCheckpointCallback:
    """Verify pipeline calls checkpoint callback at correct points."""

    @pytest.fixture()
    def mock_callback(self) -> AsyncMock:
        cb = AsyncMock()
        cb.save_pass = AsyncMock()
        cb.load_passes = AsyncMock(return_value=[])
        return cb

    @pytest.mark.asyncio()
    async def test_pipeline_saves_after_layout_pass(self, mock_callback: AsyncMock) -> None:
        """Pipeline should call save_pass after layout pass completes."""
        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = (
            '{"template_name": "basic_1col", "reasoning": "test", "section_decisions": []}'
        )
        mock_response.usage = None
        mock_provider.complete = AsyncMock(return_value=mock_response)

        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        pipeline = ScaffolderPipeline(
            mock_provider,
            "test-model",
            checkpoint_callback=mock_callback,
            run_id="test-run-123",
        )

        with (
            patch.object(pipeline, "_content_pass", new_callable=AsyncMock) as mc,
            patch.object(pipeline, "_design_pass", new_callable=AsyncMock) as md,
        ):
            mc.return_value = (SlotFill(slot_id="h", content="x"),)
            md.return_value = DesignTokens()
            await pipeline.execute("test brief")

        # At least one save_pass call for layout
        assert mock_callback.save_pass.call_count >= 1
        first_checkpoint = mock_callback.save_pass.call_args_list[0][0][0]
        assert first_checkpoint.pass_name == "layout"

    @pytest.mark.asyncio()
    async def test_pipeline_saves_after_content_design_pass(self, mock_callback: AsyncMock) -> None:
        """Pipeline should call save_pass after content+design passes complete."""
        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = (
            '{"template_name": "basic_1col", "reasoning": "test", "section_decisions": []}'
        )
        mock_response.usage = None
        mock_provider.complete = AsyncMock(return_value=mock_response)

        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        pipeline = ScaffolderPipeline(
            mock_provider,
            "test-model",
            checkpoint_callback=mock_callback,
            run_id="test-run-123",
        )

        with (
            patch.object(pipeline, "_content_pass", new_callable=AsyncMock) as mc,
            patch.object(pipeline, "_design_pass", new_callable=AsyncMock) as md,
        ):
            mc.return_value = (SlotFill(slot_id="h", content="x"),)
            md.return_value = DesignTokens()
            await pipeline.execute("test brief")

        assert mock_callback.save_pass.call_count == 2
        second_checkpoint = mock_callback.save_pass.call_args_list[1][0][0]
        assert second_checkpoint.pass_name == "content_design"

    @pytest.mark.asyncio()
    async def test_resume_skips_completed_passes(self, mock_callback: AsyncMock) -> None:
        """When resuming with cached layout, layout pass should be skipped."""
        mock_callback.load_passes.return_value = [
            PipelineCheckpoint(
                run_id="test-run-123",
                pass_name="layout",
                pass_index=0,
                data={
                    "template_name": "basic_1col",
                    "reasoning": "cached",
                    "section_order": [],
                    "fallback_template": None,
                    "section_decisions": [],
                    "slot_details": [
                        {"slot_id": "h", "slot_type": "text", "max_chars": 100, "required": True}
                    ],
                },
            ),
        ]

        mock_provider = AsyncMock()

        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        pipeline = ScaffolderPipeline(
            mock_provider,
            "test-model",
            checkpoint_callback=mock_callback,
            run_id="test-run-123",
        )

        with (
            patch.object(pipeline, "_layout_pass") as mock_layout,
            patch.object(pipeline, "_content_pass", new_callable=AsyncMock) as mc,
            patch.object(pipeline, "_design_pass", new_callable=AsyncMock) as md,
        ):
            mc.return_value = (SlotFill(slot_id="h", content="x"),)
            md.return_value = DesignTokens()
            await pipeline.execute("test brief", resume=True)

        # Layout pass should NOT have been called — it was resumed from checkpoint
        mock_layout.assert_not_called()

    @pytest.mark.asyncio()
    async def test_checkpoint_failure_does_not_crash_pipeline(self) -> None:
        """Checkpoint save failure should log but not crash the pipeline."""
        failing_cb = AsyncMock()
        failing_cb.save_pass = AsyncMock(side_effect=RuntimeError("DB gone"))
        failing_cb.load_passes = AsyncMock(return_value=[])

        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = (
            '{"template_name": "basic_1col", "reasoning": "test", "section_decisions": []}'
        )
        mock_response.usage = None
        mock_provider.complete = AsyncMock(return_value=mock_response)

        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        pipeline = ScaffolderPipeline(
            mock_provider,
            "test-model",
            checkpoint_callback=failing_cb,
            run_id="test-run-123",
        )

        with (
            patch.object(pipeline, "_content_pass", new_callable=AsyncMock) as mc,
            patch.object(pipeline, "_design_pass", new_callable=AsyncMock) as md,
        ):
            mc.return_value = (SlotFill(slot_id="h", content="x"),)
            md.return_value = DesignTokens()
            # Should complete without raising
            plan = await pipeline.execute("test brief")

        assert plan.template.template_name == "basic_1col"

    @pytest.mark.asyncio()
    async def test_no_checkpoint_when_callback_is_none(self) -> None:
        """Pipeline runs normally without checkpoint callback."""
        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = (
            '{"template_name": "basic_1col", "reasoning": "test", "section_decisions": []}'
        )
        mock_response.usage = None
        mock_provider.complete = AsyncMock(return_value=mock_response)

        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        pipeline = ScaffolderPipeline(
            mock_provider,
            "test-model",
            checkpoint_callback=None,
            run_id="",
        )

        with (
            patch.object(pipeline, "_content_pass", new_callable=AsyncMock) as mc,
            patch.object(pipeline, "_design_pass", new_callable=AsyncMock) as md,
        ):
            mc.return_value = (SlotFill(slot_id="h", content="x"),)
            md.return_value = DesignTokens()
            plan = await pipeline.execute("test brief")

        assert plan.template.template_name == "basic_1col"
