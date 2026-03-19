"""Tests for PenpotDesignSyncService."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.design_sync.penpot.service import (
    PenpotDesignSyncService,
    extract_file_id,
)
from app.design_sync.protocol import DesignNodeType, DesignSyncProvider


def _make_cm_client(**method_returns: object) -> AsyncMock:
    """Create an AsyncMock PenpotClient that works as async context manager.

    The service uses ``async with self._make_client(...) as client:``,
    so the mock returned by ``_make_client`` must support ``__aenter__``.
    """
    client = AsyncMock()
    for method, return_value in method_returns.items():
        getattr(client, method).return_value = return_value
    # Make it work as async context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestPenpotProtocol:
    def test_implements_provider_protocol(self) -> None:
        assert isinstance(PenpotDesignSyncService(), DesignSyncProvider)


class TestExtractFileId:
    def test_from_workspace_url(self) -> None:
        url = "https://design.penpot.app/#/workspace/aabb0011-2233-4455-6677-889900aabbcc/ddeeff01-2345-6789-abcd-ef0123456789"
        assert extract_file_id(url) == "ddeeff01-2345-6789-abcd-ef0123456789"

    def test_from_view_url(self) -> None:
        url = "https://design.penpot.app/#/view/abc-def-1234-5678"
        assert extract_file_id(url) == "abc-def-1234-5678"

    def test_raw_uuid(self) -> None:
        assert (
            extract_file_id("abcdef01-2345-6789-abcd-ef0123456789")
            == "abcdef01-2345-6789-abcd-ef0123456789"
        )

    def test_invalid_url_raises(self) -> None:
        from app.design_sync.exceptions import SyncFailedError

        with pytest.raises(SyncFailedError):
            extract_file_id("not-a-valid-url")


class TestPenpotSyncTokens:
    """Test token extraction from mock Penpot file data."""

    @pytest.fixture()
    def service(self) -> PenpotDesignSyncService:
        return PenpotDesignSyncService()

    @pytest.fixture()
    def mock_file_data(self) -> dict[str, object]:
        return {
            "name": "Test Email",
            "data": {
                "colors": {
                    "c1": {"name": "Primary", "color": "#FF5733", "opacity": 1.0},
                    "c2": {"name": "Background", "color": "#FFFFFF", "opacity": 1.0},
                },
                "typographies": {
                    "t1": {
                        "name": "Heading",
                        "font-family": "Inter",
                        "font-weight": "700",
                        "font-size": 24,
                        "line-height": 1.2,
                    },
                    "t2": {
                        "name": "Body",
                        "font-family": "Roboto",
                        "font-weight": "400",
                        "font-size": 16,
                        "line-height": 1.5,
                    },
                },
                "pages": ["page-1"],
                "pages-index": {
                    "page-1": {
                        "objects": {
                            "page-1": {
                                "name": "Email Design",
                                "type": "frame",
                                "shapes": ["frame-1"],
                            },
                            "frame-1": {
                                "name": "Header",
                                "type": "frame",
                                "layout": "flex",
                                "layout-gap": {"row-gap": 16, "column-gap": 8},
                                "layout-padding": {"p1": 20, "p2": 20},
                                "selrect": {
                                    "x": 0,
                                    "y": 0,
                                    "width": 600,
                                    "height": 100,
                                },
                                "shapes": [],
                            },
                        },
                    },
                },
            },
        }

    @pytest.mark.asyncio()
    async def test_sync_tokens_colors(
        self, service: PenpotDesignSyncService, mock_file_data: dict[str, object]
    ) -> None:
        client = _make_cm_client(get_file=mock_file_data)
        with patch.object(service, "_make_client", return_value=client):
            tokens = await service.sync_tokens("file-id", "token")

        assert len(tokens.colors) == 2
        assert tokens.colors[0].name == "Primary"
        assert tokens.colors[0].hex == "#FF5733"

    @pytest.mark.asyncio()
    async def test_sync_tokens_typography(
        self, service: PenpotDesignSyncService, mock_file_data: dict[str, object]
    ) -> None:
        client = _make_cm_client(get_file=mock_file_data)
        with patch.object(service, "_make_client", return_value=client):
            tokens = await service.sync_tokens("file-id", "token")

        assert len(tokens.typography) == 2
        assert tokens.typography[0].family == "Inter"

    @pytest.mark.asyncio()
    async def test_sync_tokens_spacing(
        self, service: PenpotDesignSyncService, mock_file_data: dict[str, object]
    ) -> None:
        client = _make_cm_client(get_file=mock_file_data)
        with patch.object(service, "_make_client", return_value=client):
            tokens = await service.sync_tokens("file-id", "token")

        assert len(tokens.spacing) >= 2  # row-gap + column-gap at minimum

    @pytest.mark.asyncio()
    async def test_get_file_structure(
        self, service: PenpotDesignSyncService, mock_file_data: dict[str, object]
    ) -> None:
        client = _make_cm_client(get_file=mock_file_data)
        with patch.object(service, "_make_client", return_value=client):
            structure = await service.get_file_structure("file-id", "token")

        assert structure.file_name == "Test Email"
        assert len(structure.pages) == 1
        assert structure.pages[0].children[0].name == "Header"
        assert structure.pages[0].children[0].type == DesignNodeType.FRAME


class TestPenpotListComponents:
    @pytest.mark.asyncio()
    async def test_list_components(self) -> None:
        service = PenpotDesignSyncService()
        file_data = {
            "data": {
                "components": {
                    "comp-1": {"name": "Button", "annotation": "Primary CTA"},
                    "comp-2": {"name": "Header", "path": "email/sections"},
                },
            },
        }
        client = _make_cm_client(get_file=file_data)
        with patch.object(service, "_make_client", return_value=client):
            components = await service.list_components("file-id", "token")

        assert len(components) == 2
        assert components[0].name == "Button"
        assert components[0].description == "Primary CTA"


class TestPenpotValidateConnection:
    @pytest.mark.asyncio()
    async def test_validate_success(self) -> None:
        service = PenpotDesignSyncService()
        client = _make_cm_client(validate=True, get_file={"name": "Test"})
        with patch.object(service, "_make_client", return_value=client):
            result = await service.validate_connection("file-id", "token")

        assert result is True
        client.validate.assert_awaited_once()
        client.get_file.assert_awaited_once_with("file-id")

    @pytest.mark.asyncio()
    async def test_validate_auth_failure(self) -> None:
        from app.design_sync.exceptions import SyncFailedError

        service = PenpotDesignSyncService()
        client = _make_cm_client(validate=False)
        with patch.object(service, "_make_client", return_value=client):
            with pytest.raises(SyncFailedError, match="validation failed"):
                await service.validate_connection("file-id", "token")


class TestPenpotExportImages:
    @pytest.mark.asyncio()
    async def test_export_returns_placeholder_urls(self) -> None:
        service = PenpotDesignSyncService()
        file_data: dict[str, object] = {
            "data": {
                "pages-index": {
                    "page-1": {
                        "objects": {"node-a": {}, "node-b": {}},
                    },
                },
            },
        }
        client = _make_cm_client(get_file=file_data)
        with patch.object(service, "_make_client", return_value=client):
            images = await service.export_images("file-id", "token", ["node-a"])

        assert len(images) == 1
        assert "penpot://export/" in images[0].url
        assert images[0].node_id == "node-a"

    @pytest.mark.asyncio()
    async def test_export_skips_missing_nodes(self) -> None:
        service = PenpotDesignSyncService()
        file_data: dict[str, object] = {"data": {"pages-index": {}}}
        client = _make_cm_client(get_file=file_data)
        with patch.object(service, "_make_client", return_value=client):
            images = await service.export_images("file-id", "token", ["missing-id"])

        assert len(images) == 0
