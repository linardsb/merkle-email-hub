"""Tests for design sync module."""

from datetime import UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.design_sync.crypto import decrypt_token, encrypt_token
from app.design_sync.exceptions import (
    SyncFailedError,
    UnsupportedProviderError,
)
from app.design_sync.figma.service import FigmaDesignSyncService, extract_file_key
from app.design_sync.models import DesignImport
from app.design_sync.protocol import (
    DesignComponent,
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    DesignSyncProvider,
    ExportedImage,
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)
from app.design_sync.repository import DesignSyncRepository
from app.design_sync.schemas import ConnectionResponse
from app.design_sync.service import SUPPORTED_PROVIDERS, DesignSyncService

# ── Crypto Tests ──


class TestCrypto:
    def test_round_trip(self):
        plaintext = "figd_test_token_12345"
        encrypted = encrypt_token(plaintext)
        assert encrypted != plaintext
        assert decrypt_token(encrypted) == plaintext

    def test_different_ciphertexts(self):
        plaintext = "figd_test_token_12345"
        a = encrypt_token(plaintext)
        b = encrypt_token(plaintext)
        # Fernet includes timestamp so ciphertexts differ
        assert a != b
        assert decrypt_token(a) == plaintext
        assert decrypt_token(b) == plaintext


# ── Figma File Key Extraction ──


class TestExtractFileKey:
    def test_design_url(self):
        url = "https://www.figma.com/design/aBcDeFgH123/My-Design"
        assert extract_file_key(url) == "aBcDeFgH123"

    def test_file_url(self):
        url = "https://www.figma.com/file/xYz789AbC/Another-File"
        assert extract_file_key(url) == "xYz789AbC"

    def test_invalid_url(self):
        with pytest.raises(SyncFailedError, match="Invalid Figma URL"):
            extract_file_key("https://example.com/not-figma")


# ── Protocol Compliance ──


class TestProtocol:
    def test_figma_implements_protocol(self):
        assert isinstance(FigmaDesignSyncService(), DesignSyncProvider)

    def test_all_providers_registered(self):
        assert set(SUPPORTED_PROVIDERS.keys()) == {"figma", "sketch", "canva", "penpot"}


# ── Service Tests ──


class TestDesignSyncService:
    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> DesignSyncService:
        return DesignSyncService(mock_db)

    def test_unsupported_provider(self, service: DesignSyncService) -> None:
        with pytest.raises(UnsupportedProviderError, match="not supported"):
            service._get_provider("adobe_xd")

    def test_supported_providers(self, service: DesignSyncService) -> None:
        for name in ("figma", "sketch", "canva"):
            provider = service._get_provider(name)
            assert isinstance(provider, DesignSyncProvider)

    def test_provider_caching(self, service: DesignSyncService) -> None:
        p1 = service._get_provider("figma")
        p2 = service._get_provider("figma")
        assert p1 is p2

    def test_extract_file_ref_figma(self, service: DesignSyncService) -> None:
        ref = service._extract_file_ref("figma", "https://www.figma.com/design/abc123/My-File")
        assert ref == "abc123"

    def test_extract_file_ref_stub(self, service: DesignSyncService) -> None:
        url = "https://sketch.cloud/s/something"
        ref = service._extract_file_ref("sketch", url)
        assert ref == url


# ── Schema Tests ──


class TestSchemas:
    def test_connection_response_from_model(self):
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.name = "Test"
        mock_conn.provider = "figma"
        mock_conn.file_ref = "abc123"
        mock_conn.file_url = "https://figma.com/design/abc123/Test"
        mock_conn.token_last4 = "x7Kz"
        mock_conn.status = "connected"
        mock_conn.error_message = None
        mock_conn.last_synced_at = None
        mock_conn.project_id = None
        mock_conn.created_at = "2026-01-01T00:00:00"
        mock_conn.updated_at = "2026-01-01T00:00:00"

        # Patch isinstance check
        with patch("app.design_sync.schemas.isinstance", return_value=True):
            resp = ConnectionResponse.from_model(mock_conn, project_name="My Project")

        assert resp.file_key == "abc123"
        assert resp.access_token_last4 == "x7Kz"
        assert resp.project_name == "My Project"


# ── Extracted Tokens ──


class TestExtractedTokens:
    def test_defaults(self):
        tokens = ExtractedTokens()
        assert tokens.colors == []
        assert tokens.typography == []
        assert tokens.spacing == []

    def test_with_data(self):
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Primary", hex="#538FE4", opacity=1.0)],
            typography=[
                ExtractedTypography(
                    name="H1", family="Inter", weight="700", size=32, line_height=40
                )
            ],
            spacing=[ExtractedSpacing(name="md", value=16)],
        )
        assert len(tokens.colors) == 1
        assert tokens.colors[0].hex == "#538FE4"
        assert tokens.typography[0].family == "Inter"
        assert tokens.spacing[0].value == 16


# ── Sketch/Canva Stub Tests ──


class TestStubProviders:
    @pytest.mark.asyncio
    async def test_sketch_validate(self):
        from app.design_sync.sketch.service import SketchDesignSyncService

        svc = SketchDesignSyncService()
        assert await svc.validate_connection("ref", "token") is True

    @pytest.mark.asyncio
    async def test_sketch_sync(self):
        from app.design_sync.sketch.service import SketchDesignSyncService

        svc = SketchDesignSyncService()
        tokens = await svc.sync_tokens("ref", "token")
        assert tokens == ExtractedTokens()

    @pytest.mark.asyncio
    async def test_canva_validate(self):
        from app.design_sync.canva.service import CanvaDesignSyncService

        svc = CanvaDesignSyncService()
        assert await svc.validate_connection("ref", "token") is True

    @pytest.mark.asyncio
    async def test_canva_sync(self):
        from app.design_sync.canva.service import CanvaDesignSyncService

        svc = CanvaDesignSyncService()
        tokens = await svc.sync_tokens("ref", "token")
        assert tokens == ExtractedTokens()


# ── New Protocol Dataclass Tests ──


class TestDesignNodeType:
    def test_figma_type_mapping(self) -> None:
        from app.design_sync.figma.service import _FIGMA_NODE_TYPE_MAP

        assert _FIGMA_NODE_TYPE_MAP["CANVAS"] == DesignNodeType.PAGE
        assert _FIGMA_NODE_TYPE_MAP["FRAME"] == DesignNodeType.FRAME
        assert _FIGMA_NODE_TYPE_MAP["TEXT"] == DesignNodeType.TEXT

    def test_unknown_type_defaults_to_other(self) -> None:
        from app.design_sync.figma.service import _FIGMA_NODE_TYPE_MAP

        assert (
            _FIGMA_NODE_TYPE_MAP.get("UNKNOWN_FANCY_TYPE", DesignNodeType.OTHER)
            == DesignNodeType.OTHER
        )


class TestDesignFileStructure:
    def test_empty_structure(self) -> None:
        structure = DesignFileStructure(file_name="Test")
        assert structure.file_name == "Test"
        assert structure.pages == []

    def test_with_pages(self) -> None:
        page = DesignNode(id="0:1", name="Page 1", type=DesignNodeType.PAGE)
        structure = DesignFileStructure(file_name="Test", pages=[page])
        assert len(structure.pages) == 1
        assert structure.pages[0].name == "Page 1"


class TestDesignComponent:
    def test_defaults(self) -> None:
        comp = DesignComponent(component_id="1:2", name="Button")
        assert comp.description == ""
        assert comp.thumbnail_url is None
        assert comp.containing_page is None


class TestExportedImage:
    def test_with_expiry(self) -> None:
        from datetime import datetime

        now = datetime.now(tz=UTC)
        img = ExportedImage(
            node_id="1:2", url="https://cdn.figma.com/img", format="png", expires_at=now
        )
        assert img.expires_at == now

    def test_without_expiry(self) -> None:
        img = ExportedImage(node_id="1:2", url="https://cdn.figma.com/img", format="png")
        assert img.expires_at is None


# ── Figma Provider: File Structure Parsing ──


class TestFigmaFileStructure:
    """Test Figma JSON -> DesignFileStructure parsing."""

    @pytest.fixture
    def figma_service(self) -> FigmaDesignSyncService:
        return FigmaDesignSyncService()

    @pytest.fixture
    def sample_figma_document(self) -> dict[str, Any]:
        return {
            "name": "My Design File",
            "document": {
                "id": "0:0",
                "type": "DOCUMENT",
                "children": [
                    {
                        "id": "0:1",
                        "type": "CANVAS",
                        "name": "Page 1",
                        "children": [
                            {
                                "id": "1:1",
                                "type": "FRAME",
                                "name": "Header",
                                "absoluteBoundingBox": {
                                    "x": 0,
                                    "y": 0,
                                    "width": 600,
                                    "height": 100,
                                },
                                "children": [
                                    {
                                        "id": "1:2",
                                        "type": "TEXT",
                                        "name": "Title",
                                        "absoluteBoundingBox": {
                                            "x": 0,
                                            "y": 0,
                                            "width": 200,
                                            "height": 40,
                                        },
                                        "children": [],
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "id": "0:2",
                        "type": "CANVAS",
                        "name": "Page 2",
                        "children": [],
                    },
                ],
            },
        }

    def test_parse_node_basic(self, figma_service: FigmaDesignSyncService) -> None:
        node_data: dict[str, Any] = {
            "id": "1:1",
            "type": "FRAME",
            "name": "Header",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 600, "height": 100},
            "children": [],
        }
        node = figma_service._parse_node(node_data, current_depth=0, max_depth=2)
        assert node.id == "1:1"
        assert node.name == "Header"
        assert node.type == DesignNodeType.FRAME
        assert node.width == 600
        assert node.height == 100

    def test_parse_node_depth_limit(self, figma_service: FigmaDesignSyncService) -> None:
        node_data: dict[str, Any] = {
            "id": "0:1",
            "type": "CANVAS",
            "name": "Page",
            "children": [
                {
                    "id": "1:1",
                    "type": "FRAME",
                    "name": "Frame",
                    "children": [{"id": "2:1", "type": "TEXT", "name": "Deep"}],
                }
            ],
        }
        # depth 1: should include Frame but not Deep
        node = figma_service._parse_node(node_data, current_depth=0, max_depth=1)
        assert len(node.children) == 1
        assert node.children[0].name == "Frame"
        assert node.children[0].children == []  # cut off at depth

    def test_parse_node_unlimited_depth(self, figma_service: FigmaDesignSyncService) -> None:
        node_data: dict[str, Any] = {
            "id": "0:1",
            "type": "CANVAS",
            "name": "Page",
            "children": [
                {
                    "id": "1:1",
                    "type": "FRAME",
                    "name": "Frame",
                    "children": [{"id": "2:1", "type": "TEXT", "name": "Deep", "children": []}],
                }
            ],
        }
        node = figma_service._parse_node(node_data, current_depth=0, max_depth=None)
        assert node.children[0].children[0].name == "Deep"

    def test_unknown_node_type(self, figma_service: FigmaDesignSyncService) -> None:
        node_data: dict[str, Any] = {
            "id": "1:1",
            "type": "SOME_NEW_TYPE",
            "name": "New",
            "children": [],
        }
        node = figma_service._parse_node(node_data, current_depth=0, max_depth=2)
        assert node.type == DesignNodeType.OTHER

    @pytest.mark.asyncio
    async def test_get_file_structure_api_call(
        self, figma_service: FigmaDesignSyncService, sample_figma_document: dict[str, Any]
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_figma_document

        with patch("app.design_sync.figma.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            structure = await figma_service.get_file_structure("abc123", "token")

        assert structure.file_name == "My Design File"
        assert len(structure.pages) == 2
        assert structure.pages[0].name == "Page 1"
        assert structure.pages[0].type == DesignNodeType.PAGE


# ── Figma Provider: Components ──


class TestFigmaComponents:
    @pytest.mark.asyncio
    async def test_list_components(self) -> None:
        service = FigmaDesignSyncService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "meta": {
                "components": [
                    {
                        "node_id": "1:1",
                        "name": "Button/Primary",
                        "description": "Primary action button",
                        "thumbnail_url": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/thumb.png",
                        "containing_frame": {"pageName": "Components"},
                    },
                    {
                        "node_id": "2:1",
                        "name": "Card/Default",
                        "description": "",
                        "containing_frame": {"pageName": "Components"},
                    },
                ]
            }
        }

        with patch("app.design_sync.figma.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            components = await service.list_components("abc123", "token")

        assert len(components) == 2
        assert components[0].name == "Button/Primary"
        assert components[0].thumbnail_url is not None
        assert components[1].thumbnail_url is None
        assert components[0].containing_page == "Components"


# ── Figma Provider: Image Export ──


class TestFigmaImageExport:
    @pytest.mark.asyncio
    async def test_export_images_basic(self) -> None:
        service = FigmaDesignSyncService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "images": {
                "1:1": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/1.png",
                "1:2": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/2.png",
            }
        }

        with patch("app.design_sync.figma.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            images = await service.export_images("abc123", "token", ["1:1", "1:2"])

        assert len(images) == 2
        assert images[0].format == "png"
        assert images[0].expires_at is not None

    @pytest.mark.asyncio
    async def test_export_images_empty_list(self) -> None:
        service = FigmaDesignSyncService()
        images = await service.export_images("abc123", "token", [])
        assert images == []

    @pytest.mark.asyncio
    async def test_export_images_invalid_format(self) -> None:
        service = FigmaDesignSyncService()
        with pytest.raises(SyncFailedError, match="Invalid export format"):
            await service.export_images("abc123", "token", ["1:1"], format="bmp")

    @pytest.mark.asyncio
    async def test_export_images_null_url_skipped(self) -> None:
        """Figma returns null URLs for nodes it can't render."""
        service = FigmaDesignSyncService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "images": {
                "1:1": "https://cdn.figma.com/img/1.png",
                "1:2": None,  # Failed to render
            }
        }

        with patch("app.design_sync.figma.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            images = await service.export_images("abc123", "token", ["1:1", "1:2"])

        assert len(images) == 1  # null URL skipped
        assert images[0].node_id == "1:1"


# ── Updated Stub Tests ──


class TestStubProvidersNewMethods:
    @pytest.mark.asyncio
    async def test_sketch_file_structure(self) -> None:
        from app.design_sync.sketch.service import SketchDesignSyncService

        svc = SketchDesignSyncService()
        structure = await svc.get_file_structure("ref", "token")
        assert structure.file_name == ""
        assert structure.pages == []

    @pytest.mark.asyncio
    async def test_sketch_list_components(self) -> None:
        from app.design_sync.sketch.service import SketchDesignSyncService

        svc = SketchDesignSyncService()
        assert await svc.list_components("ref", "token") == []

    @pytest.mark.asyncio
    async def test_sketch_export_images(self) -> None:
        from app.design_sync.sketch.service import SketchDesignSyncService

        svc = SketchDesignSyncService()
        assert await svc.export_images("ref", "token", ["1:1"]) == []

    @pytest.mark.asyncio
    async def test_canva_file_structure(self) -> None:
        from app.design_sync.canva.service import CanvaDesignSyncService

        svc = CanvaDesignSyncService()
        structure = await svc.get_file_structure("ref", "token")
        assert structure.file_name == ""
        assert structure.pages == []

    @pytest.mark.asyncio
    async def test_canva_list_components(self) -> None:
        from app.design_sync.canva.service import CanvaDesignSyncService

        svc = CanvaDesignSyncService()
        assert await svc.list_components("ref", "token") == []

    @pytest.mark.asyncio
    async def test_canva_export_images(self) -> None:
        from app.design_sync.canva.service import CanvaDesignSyncService

        svc = CanvaDesignSyncService()
        assert await svc.export_images("ref", "token", ["1:1"]) == []


# ── Schema Tests for New Responses ──


class TestNewSchemas:
    def test_design_node_response_recursive(self) -> None:
        from app.design_sync.schemas import DesignNodeResponse

        node = DesignNodeResponse(
            id="1:1",
            name="Frame",
            type="FRAME",
            children=[
                DesignNodeResponse(id="2:1", name="Text", type="TEXT", children=[]),
            ],
            width=600,
            height=100,
        )
        assert len(node.children) == 1
        assert node.children[0].name == "Text"

    def test_export_image_request_validation(self) -> None:
        from app.design_sync.schemas import ExportImageRequest

        req = ExportImageRequest(connection_id=1, node_ids=["1:1"], format="svg", scale=1.0)
        assert req.format == "svg"

        with pytest.raises(ValidationError):
            ExportImageRequest(connection_id=1, node_ids=["1:1"], format="bmp")

        with pytest.raises(ValidationError):
            ExportImageRequest(connection_id=1, node_ids=[], format="png")  # min_length=1


# ── Repository: get_import_by_template_id ──


class TestGetImportByTemplate:
    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repo(self, mock_db: AsyncMock) -> DesignSyncRepository:
        return DesignSyncRepository(mock_db)

    def _make_import(
        self,
        *,
        id: int = 1,
        connection_id: int = 10,
        project_id: int = 100,
        status: str = "completed",
        result_template_id: int | None = 42,
    ) -> MagicMock:
        imp = MagicMock(spec=DesignImport)
        imp.id = id
        imp.connection_id = connection_id
        imp.project_id = project_id
        imp.status = status
        imp.selected_node_ids = ["0:1"]
        imp.result_template_id = result_template_id
        imp.created_by_id = 1
        return imp

    @pytest.mark.asyncio
    async def test_get_import_by_template_returns_completed_import(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        """Repository returns a completed import matching result_template_id."""
        expected = self._make_import(result_template_id=42, status="completed")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        mock_db.execute.return_value = mock_result

        result = await repo.get_import_by_template_id(template_id=42, project_id=100)

        assert result is not None
        assert result is expected
        assert result.status == "completed"
        assert result.result_template_id == 42
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_import_by_template_returns_none_when_no_import(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        """Returns None when no import exists for the given template."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_import_by_template_id(template_id=999, project_id=100)

        assert result is None
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_import_by_template_returns_none_for_non_completed(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        """Returns None for non-completed imports (query filters status='completed')."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_import_by_template_id(template_id=42, project_id=100)

        assert result is None
        mock_db.execute.assert_awaited_once()
