"""Tests for design sync module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.design_sync.crypto import decrypt_token, encrypt_token
from app.design_sync.exceptions import (
    SyncFailedError,
    UnsupportedProviderError,
)
from app.design_sync.figma.service import FigmaDesignSyncService, extract_file_key
from app.design_sync.protocol import (
    DesignSyncProvider,
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)
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
        assert set(SUPPORTED_PROVIDERS.keys()) == {"figma", "sketch", "canva"}


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
