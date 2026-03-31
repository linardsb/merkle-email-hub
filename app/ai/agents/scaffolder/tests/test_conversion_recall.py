"""Tests for Scaffolder recall of conversion memory (48.5)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline


def _make_pipeline() -> ScaffolderPipeline:
    """Create a minimal pipeline for testing recall."""
    provider = MagicMock()
    return ScaffolderPipeline(provider=provider, model="test-model")


def _make_memory(content: str, has_quality_issues: bool = True) -> MagicMock:
    m = MagicMock()
    m.content = content
    m.metadata_json = {"has_quality_issues": has_quality_issues, "source": "converter_quality"}
    m.created_at = "2026-03-31T12:00:00"
    return m


class TestRecallConversionContext:
    @pytest.mark.asyncio
    async def test_with_memories(self) -> None:
        pipeline = _make_pipeline()
        mock_service = AsyncMock()
        mock_service.recall = AsyncMock(
            return_value=[
                (_make_memory("Hero section had low confidence"), 0.8),
                (_make_memory("Footer layout mismatch"), 0.7),
            ]
        )

        with (
            patch("app.core.database.get_db_context") as mock_db_ctx,
            patch("app.knowledge.embedding.get_embedding_provider"),
            patch("app.memory.service.MemoryService", return_value=mock_service),
            patch("app.core.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.design_sync.conversion_memory_enabled = True
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await pipeline.recall_conversion_context("email campaign brief", None)

        assert result is not None
        assert "## Conversion History Insights" in result
        assert "Hero section" in result
        assert "Footer layout" in result

    @pytest.mark.asyncio
    async def test_empty(self) -> None:
        pipeline = _make_pipeline()
        mock_service = AsyncMock()
        mock_service.recall = AsyncMock(return_value=[])

        with (
            patch("app.core.database.get_db_context") as mock_db_ctx,
            patch("app.knowledge.embedding.get_embedding_provider"),
            patch("app.memory.service.MemoryService", return_value=mock_service),
            patch("app.core.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.design_sync.conversion_memory_enabled = True
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await pipeline.recall_conversion_context("brief", None)

        assert result is None

    @pytest.mark.asyncio
    async def test_filters_clean_conversions(self) -> None:
        pipeline = _make_pipeline()
        mock_service = AsyncMock()
        mock_service.recall = AsyncMock(
            return_value=[
                (_make_memory("Clean conversion", has_quality_issues=False), 0.9),
                (_make_memory("Bad conversion", has_quality_issues=True), 0.7),
            ]
        )

        with (
            patch("app.core.database.get_db_context") as mock_db_ctx,
            patch("app.knowledge.embedding.get_embedding_provider"),
            patch("app.memory.service.MemoryService", return_value=mock_service),
            patch("app.core.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.design_sync.conversion_memory_enabled = True
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await pipeline.recall_conversion_context("brief", None)

        assert result is not None
        assert "Bad conversion" in result
        assert "Clean conversion" not in result

    @pytest.mark.asyncio
    async def test_respects_config_gate(self) -> None:
        pipeline = _make_pipeline()

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.design_sync.conversion_memory_enabled = False
            result = await pipeline.recall_conversion_context("brief", None)

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_errors_gracefully(self) -> None:
        pipeline = _make_pipeline()

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch(
                "app.core.database.get_db_context",
                side_effect=RuntimeError("DB down"),
            ),
        ):
            mock_settings.return_value.design_sync.conversion_memory_enabled = True
            result = await pipeline.recall_conversion_context("brief", None)

        assert result is None
