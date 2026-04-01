"""Tests for FigmaDesignSyncService.export_frame_screenshots()."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.design_sync.protocol import ExportedImage


def _make_exported(
    node_id: str,
    url: str = "https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/test.png",
) -> ExportedImage:
    return ExportedImage(
        node_id=node_id,
        url=url,
        format="png",
        expires_at=datetime.now(tz=UTC),
    )


def _make_service() -> MagicMock:
    """Build a mock FigmaDesignSyncService with export_images + download_image_bytes."""
    svc = MagicMock()
    svc.export_images = AsyncMock(return_value=[])
    svc.download_image_bytes = AsyncMock(return_value=b"")
    return svc


class TestExportFrameScreenshots:
    @pytest.mark.asyncio
    async def test_batch_happy_path(self) -> None:
        """Two node_ids → dict with 2 entries and correct bytes."""
        from app.design_sync.figma.service import FigmaDesignSyncService

        img_a = _make_exported("100:1")
        img_b = _make_exported("100:2")
        bytes_a = b"PNG-A"
        bytes_b = b"PNG-B"

        svc = _make_service()
        svc.export_images = AsyncMock(return_value=[img_a, img_b])
        svc.download_image_bytes = AsyncMock(side_effect=[bytes_a, bytes_b])

        result = await FigmaDesignSyncService.export_frame_screenshots(
            svc,
            "file_key",
            "token",
            ["100:1", "100:2"],
            scale=2.0,
        )

        assert result == {"100:1": bytes_a, "100:2": bytes_b}
        svc.export_images.assert_awaited_once()
        assert svc.download_image_bytes.await_count == 2

    @pytest.mark.asyncio
    async def test_empty_node_ids(self) -> None:
        """Empty list → empty dict, export_images not called."""
        from app.design_sync.figma.service import FigmaDesignSyncService

        svc = _make_service()

        result = await FigmaDesignSyncService.export_frame_screenshots(
            svc,
            "file_key",
            "token",
            [],
        )

        assert result == {}
        svc.export_images.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_partial_download_failure(self) -> None:
        """3 nodes, 1 download raises → dict has 2 entries."""
        from app.design_sync.figma.service import FigmaDesignSyncService

        img_a = _make_exported("1:1")
        img_b = _make_exported("1:2")
        img_c = _make_exported("1:3")

        svc = _make_service()
        svc.export_images = AsyncMock(return_value=[img_a, img_b, img_c])
        svc.download_image_bytes = AsyncMock(
            side_effect=[b"OK-A", TimeoutError("CDN timeout"), b"OK-C"],
        )

        result = await FigmaDesignSyncService.export_frame_screenshots(
            svc,
            "file_key",
            "token",
            ["1:1", "1:2", "1:3"],
        )

        assert len(result) == 2
        assert result["1:1"] == b"OK-A"
        assert "1:2" not in result
        assert result["1:3"] == b"OK-C"

    @pytest.mark.asyncio
    async def test_export_returns_empty(self) -> None:
        """export_images returns [] → empty dict."""
        from app.design_sync.figma.service import FigmaDesignSyncService

        svc = _make_service()
        svc.export_images = AsyncMock(return_value=[])

        result = await FigmaDesignSyncService.export_frame_screenshots(
            svc,
            "file_key",
            "token",
            ["100:1"],
        )

        assert result == {}
        svc.download_image_bytes.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_scale_forwarded(self) -> None:
        """Verify scale kwarg is passed through to export_images."""
        from app.design_sync.figma.service import FigmaDesignSyncService

        svc = _make_service()
        svc.export_images = AsyncMock(return_value=[])

        await FigmaDesignSyncService.export_frame_screenshots(
            svc,
            "fk",
            "tk",
            ["1:1"],
            scale=3.5,
        )

        call_kwargs = svc.export_images.call_args
        assert call_kwargs is not None
        # scale is keyword-only, check kwargs
        assert call_kwargs.kwargs["scale"] == 3.5
        assert call_kwargs.kwargs["format"] == "png"
