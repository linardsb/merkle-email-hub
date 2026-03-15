"""Tests for design asset storage pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.design_sync.assets import (
    DesignAssetService,
    _get_asset_path,
    _sanitize_node_id,
    _try_resize_image,
)
from app.design_sync.exceptions import AssetNotFoundError

# ── Helpers ──


class TestSanitizeNodeId:
    def test_colon_replaced(self) -> None:
        assert _sanitize_node_id("1:2") == "1_2"

    def test_no_colons(self) -> None:
        assert _sanitize_node_id("abc") == "abc"

    def test_multiple_colons(self) -> None:
        assert _sanitize_node_id("1:2:3") == "1_2_3"


class TestGetAssetPath:
    @patch("app.design_sync.assets.get_settings")
    def test_valid_path(self, mock_settings: MagicMock, tmp_path: Path) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        path = _get_asset_path(42, "1:2", "png")
        assert path == tmp_path / "42" / "1_2.png"

    @patch("app.design_sync.assets.get_settings")
    def test_invalid_filename_rejected(self, mock_settings: MagicMock, tmp_path: Path) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        with pytest.raises(AssetNotFoundError):
            _get_asset_path(42, "../etc/passwd", "png")


# ── Resize ──


class TestTryResizeImage:
    def test_svg_skipped(self) -> None:
        data = b"<svg>...</svg>"
        assert _try_resize_image(data, 600, "svg") is data

    def test_pdf_skipped(self) -> None:
        data = b"%PDF-1.4"
        assert _try_resize_image(data, 600, "pdf") is data

    def test_no_pillow_returns_original(self) -> None:
        """When Pillow is not available, original data is returned."""
        data = b"\x89PNG\r\n..."
        with patch.dict("sys.modules", {"PIL": None, "PIL.Image": None}):
            result = _try_resize_image(data, 600, "png")
        # Should return original (may fail to import PIL)
        assert isinstance(result, bytes)


# ── DesignAssetService ──


class TestDesignAssetService:
    @pytest.fixture
    def asset_service(self) -> DesignAssetService:
        return DesignAssetService()

    @patch("app.design_sync.assets.get_settings")
    def test_get_stored_path_valid(
        self, mock_settings: MagicMock, asset_service: DesignAssetService, tmp_path: Path
    ) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        # Create the file
        conn_dir = tmp_path / "1"
        conn_dir.mkdir()
        (conn_dir / "1_2.png").write_bytes(b"fake png")

        path = asset_service.get_stored_path(1, "1_2.png")
        assert path.is_file()

    @patch("app.design_sync.assets.get_settings")
    def test_get_stored_path_traversal_blocked(
        self, mock_settings: MagicMock, asset_service: DesignAssetService, tmp_path: Path
    ) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        with pytest.raises(AssetNotFoundError):
            asset_service.get_stored_path(1, "../../../etc/passwd")

    @patch("app.design_sync.assets.get_settings")
    def test_get_stored_path_missing_file(
        self, mock_settings: MagicMock, asset_service: DesignAssetService, tmp_path: Path
    ) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        with pytest.raises(AssetNotFoundError):
            asset_service.get_stored_path(1, "nonexistent.png")

    @patch("app.design_sync.assets.get_settings")
    def test_delete_connection_assets(
        self, mock_settings: MagicMock, asset_service: DesignAssetService, tmp_path: Path
    ) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        conn_dir = tmp_path / "1"
        conn_dir.mkdir()
        (conn_dir / "a.png").write_bytes(b"fake")
        (conn_dir / "b.png").write_bytes(b"fake")

        count = asset_service.delete_connection_assets(1)
        assert count == 2
        assert not conn_dir.exists()

    @patch("app.design_sync.assets.get_settings")
    def test_delete_nonexistent_connection(
        self, mock_settings: MagicMock, asset_service: DesignAssetService, tmp_path: Path
    ) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        assert asset_service.delete_connection_assets(999) == 0

    @patch("app.design_sync.assets.get_settings")
    def test_list_stored_assets(
        self, mock_settings: MagicMock, asset_service: DesignAssetService, tmp_path: Path
    ) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        conn_dir = tmp_path / "1"
        conn_dir.mkdir()
        (conn_dir / "1_2.png").write_bytes(b"fake")
        (conn_dir / "3_4.png").write_bytes(b"fake")

        result = asset_service.list_stored_assets(1)
        assert result == ["1_2.png", "3_4.png"]

    @pytest.mark.asyncio
    @patch("app.design_sync.assets.get_settings")
    async def test_download_and_store(
        self, mock_settings: MagicMock, asset_service: DesignAssetService, tmp_path: Path
    ) -> None:
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        mock_settings.return_value.design_sync.asset_max_width = 1200

        fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_image_bytes

        with patch("app.design_sync.assets.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            stored = await asset_service.download_and_store(
                connection_id=1,
                images=[
                    {"node_id": "1:2", "url": "https://cdn.figma.com/img/1.png"},
                    {"node_id": "3:4", "url": "https://cdn.figma.com/img/2.png"},
                ],
                fmt="png",
            )

        assert len(stored) == 2
        assert stored[0]["node_id"] == "1:2"
        assert stored[0]["filename"] == "1_2.png"
        assert (tmp_path / "1" / "1_2.png").is_file()
        assert (tmp_path / "1" / "3_4.png").is_file()

    @pytest.mark.asyncio
    @patch("app.design_sync.assets.get_settings")
    async def test_download_partial_failure(
        self, mock_settings: MagicMock, asset_service: DesignAssetService, tmp_path: Path
    ) -> None:
        """Failed downloads are skipped, successful ones are stored."""
        mock_settings.return_value.design_sync.asset_storage_path = str(tmp_path)
        mock_settings.return_value.design_sync.asset_max_width = 1200

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.content = b"good image"

        fail_response = MagicMock()
        fail_response.status_code = 500

        call_count = 0

        async def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ok_response
            return fail_response

        with patch("app.design_sync.assets.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=side_effect)
            mock_client_cls.return_value = mock_client

            stored = await asset_service.download_and_store(
                connection_id=1,
                images=[
                    {"node_id": "1:1", "url": "https://cdn.figma.com/ok.png"},
                    {"node_id": "2:2", "url": "https://cdn.figma.com/fail.png"},
                ],
                fmt="png",
            )

        assert len(stored) == 1
        assert stored[0]["node_id"] == "1:1"
