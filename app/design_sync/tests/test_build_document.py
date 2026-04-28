# pyright: reportPrivateUsage=false
"""Tests for adapter build_document() methods (Phase 36.3).

Covers:
- Figma adapter build_document() returns valid EmailDesignDocument
- Penpot adapter build_document() returns valid EmailDesignDocument
- Token validation and tree normalization are applied
- sync_connection() delegates to build_document() when available
- sync_connection() falls back to legacy path for stub providers
- build_document() output matches from_legacy() for same input
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.design_sync.email_design_document import EmailDesignDocument
from app.design_sync.figma.service import FigmaDesignSyncService
from app.design_sync.penpot.service import PenpotDesignSyncService
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)
from app.design_sync.schemas import ConnectionResponse
from app.design_sync.service import DesignSyncService

# ── Factories ──


def _make_tokens() -> ExtractedTokens:
    return ExtractedTokens(
        colors=[
            ExtractedColor(name="Background", hex="#FFFFFF"),
            ExtractedColor(name="Primary", hex="#0066CC"),
        ],
        typography=[
            ExtractedTypography(
                name="Heading", family="Inter", weight="700", size=32.0, line_height=40.0
            ),
            ExtractedTypography(
                name="Body", family="Inter", weight="400", size=16.0, line_height=24.0
            ),
        ],
        spacing=[ExtractedSpacing(name="s1", value=16)],
    )


def _make_structure() -> DesignFileStructure:
    hero = DesignNode(
        id="hero",
        name="Hero Section",
        type=DesignNodeType.FRAME,
        width=600,
        height=400,
        children=[
            DesignNode(
                id="hero_heading",
                name="Hero Title",
                type=DesignNodeType.TEXT,
                text_content="Welcome",
                font_size=32.0,
                font_weight=700,
                y=0,
            ),
            DesignNode(
                id="hero_img",
                name="Hero Image",
                type=DesignNodeType.IMAGE,
                width=520,
                height=200,
                y=100,
            ),
        ],
    )
    footer = DesignNode(
        id="footer",
        name="Footer",
        type=DesignNodeType.FRAME,
        width=600,
        height=60,
        children=[
            DesignNode(
                id="footer_text",
                name="Legal",
                type=DesignNodeType.TEXT,
                text_content="\u00a9 2026",
                font_size=12.0,
                y=0,
            ),
        ],
    )
    page = DesignNode(
        id="page1",
        name="Page",
        type=DesignNodeType.PAGE,
        children=[hero, footer],
    )
    return DesignFileStructure(file_name="Test.fig", pages=[page])


def _make_empty_structure() -> DesignFileStructure:
    """Structure with no visible frames."""
    page = DesignNode(
        id="page1",
        name="Page",
        type=DesignNodeType.PAGE,
        children=[],
    )
    return DesignFileStructure(file_name="Empty.fig", pages=[page])


def _make_connection(
    conn_id: int = 1,
    project_id: int | None = None,
    provider: str = "figma",
) -> MagicMock:
    conn = MagicMock()
    conn.id = conn_id
    conn.project_id = project_id
    conn.provider = provider
    conn.file_ref = "abc123"
    conn.encrypted_token = "encrypted"
    conn.config_json = None
    return conn


# ── Figma adapter tests ──


class TestFigmaBuildDocument:
    @pytest.mark.asyncio
    async def test_returns_valid_email_design_document(self) -> None:
        service = FigmaDesignSyncService()
        tokens = _make_tokens()
        structure = _make_structure()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            document, _out_tokens, _warnings, _out_structure = await service.build_document(
                "file123", "token123"
            )

        assert isinstance(document, EmailDesignDocument)
        assert document.source is not None
        assert document.source.provider == "figma"
        assert len(document.sections) >= 1
        errors = EmailDesignDocument.validate(document.to_json())
        assert not errors, f"Schema validation failed: {errors}"

    @pytest.mark.asyncio
    async def test_validates_tokens(self) -> None:
        """Token warnings are returned from validate_and_transform."""
        service = FigmaDesignSyncService()
        tokens = _make_tokens()
        structure = _make_structure()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            _doc, out_tokens, warnings, _struct = await service.build_document(
                "file123", "token123"
            )

        # validate_and_transform may or may not produce warnings for clean tokens
        assert isinstance(warnings, list)
        assert isinstance(out_tokens, ExtractedTokens)

    @pytest.mark.asyncio
    async def test_normalizes_tree(self) -> None:
        """Hidden nodes are removed by tree normalization."""
        service = FigmaDesignSyncService()
        tokens = _make_tokens()
        # Add invisible node to structure
        hidden = DesignNode(
            id="hidden",
            name="Hidden",
            type=DesignNodeType.FRAME,
            width=600,
            height=100,
            visible=False,
        )
        structure = _make_structure()
        page = structure.pages[0]
        page_with_hidden = DesignNode(
            id=page.id,
            name=page.name,
            type=page.type,
            children=[*page.children, hidden],
        )
        structure_with_hidden = DesignFileStructure(
            file_name=structure.file_name, pages=[page_with_hidden]
        )

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure_with_hidden),
        ):
            _doc, _tokens, _warnings, out_struct = await service.build_document(
                "file123", "token123"
            )

        # Hidden node should be removed by normalization
        all_ids = {c.id for p in out_struct.pages for c in p.children}
        assert "hidden" not in all_ids

    @pytest.mark.asyncio
    async def test_with_connection_config(self) -> None:
        """Container width override flows through from connection_config."""
        service = FigmaDesignSyncService()
        tokens = _make_tokens()
        structure = _make_structure()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _tokens, _warnings, _struct = await service.build_document(
                "file123",
                "token123",
                connection_config={"container_width": 700},
            )

        assert doc.layout.container_width == 700

    @pytest.mark.asyncio
    async def test_no_frames_returns_empty_sections(self) -> None:
        """Structure with no visible frames returns document with empty sections."""
        service = FigmaDesignSyncService()
        tokens = _make_tokens()
        structure = _make_empty_structure()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _tokens, _warnings, _struct = await service.build_document("file123", "token123")

        assert len(doc.sections) == 0
        assert doc.version == "1.0"


# ── Penpot adapter tests ──


class TestPenpotBuildDocument:
    @pytest.mark.asyncio
    async def test_returns_valid_email_design_document(self) -> None:
        service = PenpotDesignSyncService()
        tokens = _make_tokens()
        structure = _make_structure()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            document, _tokens, _warnings, _struct = await service.build_document(
                "file123", "token123"
            )

        assert isinstance(document, EmailDesignDocument)
        assert document.source is not None
        assert document.source.provider == "penpot"
        assert len(document.sections) >= 1

    @pytest.mark.asyncio
    async def test_source_provider_is_penpot(self) -> None:
        service = PenpotDesignSyncService()
        tokens = _make_tokens()
        structure = _make_structure()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _tokens, _warnings, _struct = await service.build_document("file123", "token123")

        assert doc.source is not None
        assert doc.source.provider == "penpot"


# ── sync_connection delegation tests ──


def _sync_patches(
    service: DesignSyncService,
    conn: MagicMock,
    mock_provider: AsyncMock | MagicMock,
    mock_save: AsyncMock | None = None,
) -> tuple[Any, ...]:
    """Return a tuple of context managers for sync_connection mocking."""
    return (
        patch.object(service._repo, "get_connection", new_callable=AsyncMock, return_value=conn),
        patch.object(service._repo, "update_status", new_callable=AsyncMock),
        patch.object(
            service._repo,
            "save_snapshot",
            mock_save if mock_save is not None else AsyncMock(),
        ),
        patch.object(service._ctx, "get_provider", return_value=mock_provider),
        patch(
            "app.design_sync.services.connection_service.decrypt_token",
            return_value="token123",
        ),
        patch(
            "app.design_sync.service.fetch_target_clients",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(service._ctx, "get_project_name", new_callable=AsyncMock, return_value="Test"),
        patch.object(ConnectionResponse, "from_model", return_value=MagicMock()),
    )


class TestSyncConnectionBuildDocument:
    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> DesignSyncService:
        return DesignSyncService(mock_db)

    @pytest.mark.asyncio
    async def test_uses_build_document_when_available(self, service: DesignSyncService) -> None:
        """sync_connection delegates to build_document when provider supports it."""
        conn = _make_connection(provider="figma")
        tokens = _make_tokens()
        structure = _make_structure()
        document = EmailDesignDocument.from_legacy(structure, tokens)

        mock_provider = AsyncMock()
        mock_provider.build_document = AsyncMock(return_value=(document, tokens, [], structure))
        mock_provider.export_images = AsyncMock(return_value=[])

        mock_save = AsyncMock()
        patches = _sync_patches(service, conn, mock_provider, mock_save)

        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
        ):
            await service.sync_connection(1, MagicMock(id=1))

        mock_provider.build_document.assert_awaited_once()
        # document_json should be stored
        save_call = mock_save.call_args
        assert save_call is not None
        doc_json = save_call.kwargs.get("document_json")
        assert doc_json is not None

    @pytest.mark.asyncio
    async def test_fallback_without_build_document(self, service: DesignSyncService) -> None:
        """Stub providers without build_document use legacy path."""
        conn = _make_connection(provider="sketch")
        tokens = _make_tokens()
        structure = _make_structure()

        mock_provider = MagicMock()
        del mock_provider.build_document
        mock_provider.sync_tokens_and_structure = AsyncMock(return_value=(tokens, structure))
        mock_provider.export_images = AsyncMock(return_value=[])

        patches = _sync_patches(service, conn, mock_provider)

        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
        ):
            await service.sync_connection(1, MagicMock(id=1))

        mock_provider.sync_tokens_and_structure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_document_validates_schema(self, service: DesignSyncService) -> None:
        """Stored document_json passes EmailDesignDocument schema validation."""
        conn = _make_connection(provider="figma")
        tokens = _make_tokens()
        structure = _make_structure()
        document = EmailDesignDocument.from_legacy(structure, tokens)

        mock_provider = AsyncMock()
        mock_provider.build_document = AsyncMock(return_value=(document, tokens, [], structure))
        mock_provider.export_images = AsyncMock(return_value=[])

        saved_doc_json: dict[str, object] | None = None

        async def capture_save(
            conn_id: int,
            tokens_dict: dict[str, object],
            document_json: dict[str, object] | None = None,
        ) -> MagicMock:
            nonlocal saved_doc_json
            saved_doc_json = document_json
            return MagicMock()

        mock_save = AsyncMock(side_effect=capture_save)
        patches = _sync_patches(service, conn, mock_provider, mock_save)

        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
        ):
            await service.sync_connection(1, MagicMock(id=1))

        assert saved_doc_json is not None
        errors = EmailDesignDocument.validate(saved_doc_json)
        assert not errors, f"Schema validation failed: {errors}"


# ── Equivalence test ──


class TestBuildDocumentEquivalence:
    @pytest.mark.asyncio
    async def test_matches_from_legacy(self) -> None:
        """build_document output matches from_legacy for same input."""
        tokens = _make_tokens()
        structure = _make_structure()

        # build_document path (via Figma adapter)
        service = FigmaDesignSyncService()
        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc_adapter, _tokens, _warnings, _struct = await service.build_document(
                "file123", "token123"
            )

        # Direct from_legacy path
        doc_legacy = EmailDesignDocument.from_legacy(structure, tokens, source_provider="figma")

        # Compare serialized JSON (handles frozen dataclass comparison)
        adapter_json = doc_adapter.to_json()
        legacy_json = doc_legacy.to_json()

        assert adapter_json["version"] == legacy_json["version"]
        assert len(adapter_json.get("sections", [])) == len(legacy_json.get("sections", []))
        assert adapter_json["source"]["provider"] == legacy_json["source"]["provider"]
        # Sections should have same types
        adapter_types = [s["type"] for s in adapter_json.get("sections", [])]
        legacy_types = [s["type"] for s in legacy_json.get("sections", [])]
        assert adapter_types == legacy_types
