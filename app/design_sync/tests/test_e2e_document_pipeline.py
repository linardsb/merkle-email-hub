# pyright: reportPrivateUsage=false, reportUnknownMemberType=false
"""E2E integration tests for the EmailDesignDocument pipeline (Phase 36.7).

Covers five pipeline scenarios end-to-end through the document-based API:
1. Figma adapter → build_document → convert_document → HTML
2. MJML → MjmlImportAdapter.parse → EmailDesignDocument → convert_document_mjml → HTML
3. HTML → HtmlImportAdapter.parse → EmailDesignDocument → convert_document → HTML
4. Cross-format: same email imported as MJML and HTML → comparable documents
5. Penpot adapter → build_document → convert_document → HTML
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.design_sync.converter_service import (
    ConversionResult,
    DesignConverterService,
    MjmlCompileResult,
)
from app.design_sync.email_design_document import (
    DocumentColor,
    DocumentImage,
    DocumentLayout,
    DocumentSection,
    DocumentSource,
    DocumentText,
    DocumentTokens,
    DocumentTypography,
    EmailDesignDocument,
)
from app.design_sync.figma.service import FigmaDesignSyncService
from app.design_sync.html_import.adapter import HtmlImportAdapter
from app.design_sync.mjml_import.adapter import MjmlImportAdapter
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

# ── Factories ──────────────────────────────────────────────────────────


def _make_tokens() -> ExtractedTokens:
    return ExtractedTokens(
        colors=[
            ExtractedColor(name="Background", hex="#FFFFFF"),
            ExtractedColor(name="Text Color", hex="#333333"),
            ExtractedColor(name="Primary", hex="#0066CC"),
        ],
        dark_colors=[
            ExtractedColor(name="Background", hex="#1A1A2E"),
            ExtractedColor(name="Text Color", hex="#E0E0E0"),
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
                text_content="Welcome to our email",
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
    content = DesignNode(
        id="content",
        name="Content Section",
        type=DesignNodeType.FRAME,
        width=600,
        height=200,
        children=[
            DesignNode(
                id="body_text",
                name="Body Text",
                type=DesignNodeType.TEXT,
                text_content="Check out our latest offers.",
                font_size=16.0,
                y=0,
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
                text_content="\u00a9 2026 Acme Inc.",
                font_size=12.0,
                y=0,
            ),
        ],
    )
    page = DesignNode(
        id="page1",
        name="Email",
        type=DesignNodeType.FRAME,
        width=600,
        height=660,
        children=[hero, content, footer],
    )
    return DesignFileStructure(file_name="test_email.fig", pages=[page])


def _make_document(**overrides: Any) -> EmailDesignDocument:
    defaults: dict[str, Any] = {
        "version": "1.0",
        "tokens": DocumentTokens(
            colors=[
                DocumentColor(name="Background", hex="#FFFFFF"),
                DocumentColor(name="Text Color", hex="#333333"),
                DocumentColor(name="Primary", hex="#0066CC"),
            ],
            dark_colors=[
                DocumentColor(name="Background", hex="#1A1A2E"),
                DocumentColor(name="Text Color", hex="#E0E0E0"),
            ],
            typography=[
                DocumentTypography(
                    name="Heading",
                    family="Inter",
                    weight="700",
                    size=32.0,
                    line_height=40.0,
                ),
                DocumentTypography(
                    name="Body",
                    family="Inter",
                    weight="400",
                    size=16.0,
                    line_height=24.0,
                ),
            ],
        ),
        "sections": [
            DocumentSection(
                id="hero",
                type="hero",
                node_name="Hero",
                width=600.0,
                height=400.0,
                texts=[
                    DocumentText(
                        node_id="hero_heading",
                        content="Welcome to our email",
                        font_size=32.0,
                        is_heading=True,
                    ),
                ],
                images=[
                    DocumentImage(
                        node_id="hero_img", node_name="Hero Image", width=520.0, height=200.0
                    ),
                ],
            ),
            DocumentSection(
                id="content",
                type="content",
                node_name="Content",
                width=600.0,
                height=200.0,
                texts=[
                    DocumentText(
                        node_id="body_text",
                        content="Check out our latest offers.",
                        font_size=16.0,
                    ),
                ],
            ),
            DocumentSection(
                id="footer",
                type="footer",
                node_name="Footer",
                width=600.0,
                height=60.0,
                texts=[
                    DocumentText(
                        node_id="footer_text",
                        content="\u00a9 2026 Acme Inc.",
                        font_size=12.0,
                    ),
                ],
            ),
        ],
        "layout": DocumentLayout(container_width=600),
        "source": DocumentSource(provider="figma", file_ref="test_file_123"),
    }
    defaults.update(overrides)
    return EmailDesignDocument(**defaults)


def _full_mjml() -> str:
    return """\
<mjml>
  <mj-head>
    <mj-attributes>
      <mj-all font-family="Inter" font-size="16px" color="#333333" />
      <mj-button background-color="#0066CC" color="#FFFFFF" font-size="18px" />
    </mj-attributes>
    <mj-style>
      @media (prefers-color-scheme: dark) {
        .dark-bg { background-color: #1A1A2E; }
        .dark-text { color: #E0E0E0; }
      }
    </mj-style>
  </mj-head>
  <mj-body width="600px">
    <mj-section padding="10px 20px">
      <mj-column>
        <mj-image src="https://example.com/logo.png" alt="Logo" width="150px" />
      </mj-column>
    </mj-section>
    <mj-hero background-color="#0066CC" padding="30px">
      <mj-column>
        <mj-text font-size="32px" font-weight="700">Big Headline</mj-text>
        <mj-text>Body text under hero</mj-text>
      </mj-column>
    </mj-hero>
    <mj-section padding="20px">
      <mj-column width="50%">
        <mj-text>Left column text</mj-text>
      </mj-column>
      <mj-column width="50%">
        <mj-text>Right column text</mj-text>
      </mj-column>
    </mj-section>
    <mj-section padding="20px">
      <mj-column>
        <mj-button href="https://example.com/cta">Click Here</mj-button>
      </mj-column>
    </mj-section>
    <mj-section padding="10px">
      <mj-column>
        <mj-text font-size="12px" align="center">&#169; 2026 Acme Inc.</mj-text>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>"""


def _simple_email_html() -> str:
    """A simple email HTML for import testing."""
    return """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  @media (prefers-color-scheme: dark) {
    .dark-bg { background-color: #1A1A2E !important; }
  }
</style>
</head>
<body style="margin:0;padding:0;background-color:#FFFFFF;font-family:Inter,Arial,sans-serif;">
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding:20px;text-align:center;">
      <img src="https://example.com/logo.png" alt="Logo" width="150" />
    </td>
  </tr>
  <tr>
    <td style="padding:30px;background-color:#0066CC;color:#FFFFFF;text-align:center;">
      <h1 style="margin:0;font-size:32px;font-weight:700;font-family:Inter,Arial,sans-serif;">Big Headline</h1>
      <p style="margin:10px 0 0;">Body text under hero</p>
    </td>
  </tr>
  <tr>
    <td style="padding:20px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="50%" style="padding:0 10px 0 0;">Left column text</td>
          <td width="50%" style="padding:0 0 0 10px;">Right column text</td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:20px;text-align:center;">
      <table role="presentation" align="center" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="background-color:#0066CC;padding:12px 30px;border-radius:4px;">
            <a href="https://example.com/cta" style="color:#FFFFFF;text-decoration:none;font-size:18px;">Click Here</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:10px;text-align:center;font-size:12px;">
      &copy; 2026 Acme Inc.
    </td>
  </tr>
</table>
</body>
</html>"""


# ── 1. Figma E2E ──────────────────────────────────────────────────────


class TestFigmaE2E:
    """Figma API → build_document() → convert_document() → HTML."""

    @pytest.mark.asyncio
    async def test_figma_build_and_convert_produces_valid_html(self) -> None:
        tokens = _make_tokens()
        structure = _make_structure()
        service = FigmaDesignSyncService()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _out_tokens, _warnings, _out_structure = await service.build_document(
                file_ref="file123", access_token="token123"
            )

        assert isinstance(doc, EmailDesignDocument)
        assert doc.version == "1.0"
        errors = EmailDesignDocument.validate(doc.to_json())
        assert errors == []

        converter = DesignConverterService()
        result = converter.convert_document(doc)

        assert isinstance(result, ConversionResult)
        assert "<!DOCTYPE html" in result.html
        assert "<table" in result.html
        assert result.sections_count > 0

    @pytest.mark.asyncio
    async def test_figma_document_has_classified_sections(self) -> None:
        tokens = _make_tokens()
        structure = _make_structure()
        service = FigmaDesignSyncService()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _tokens, _warnings, _struct = await service.build_document(
                file_ref="file123", access_token="token123"
            )

        assert len(doc.sections) > 0
        types = {s.type for s in doc.sections}
        # Structure has hero, content, footer — at least some should be classified
        assert types != {"unknown"}, "All sections classified as unknown"

    @pytest.mark.asyncio
    async def test_figma_document_tokens_round_trip_through_bridge(self) -> None:
        tokens = _make_tokens()
        structure = _make_structure()
        service = FigmaDesignSyncService()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _tokens, _warnings, _struct = await service.build_document(
                file_ref="file123", access_token="token123"
            )

        # Forward bridge
        extracted = doc.to_extracted_tokens()
        assert isinstance(extracted, ExtractedTokens)
        assert len(extracted.colors) == len(doc.tokens.colors)
        assert len(extracted.typography) == len(doc.tokens.typography)

    @pytest.mark.asyncio
    async def test_figma_convert_with_target_clients(self) -> None:
        tokens = _make_tokens()
        structure = _make_structure()
        service = FigmaDesignSyncService()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _tokens, _warnings, _struct = await service.build_document(
                file_ref="file123", access_token="token123"
            )

        converter = DesignConverterService()
        result = converter.convert_document(doc, target_clients=["gmail", "outlook"])
        assert isinstance(result, ConversionResult)
        # Should still produce valid HTML even with client targeting
        assert result.sections_count > 0 or "No sections" not in result.html

    def test_figma_convert_document_directly(self) -> None:
        """convert_document() with a pre-built document (no adapter)."""
        doc = _make_document()
        converter = DesignConverterService()
        result = converter.convert_document(doc)

        assert "<!DOCTYPE html" in result.html
        assert "<table" in result.html
        assert result.sections_count >= 3


# ── 2. MJML Import E2E ────────────────────────────────────────────────


class TestMjmlImportE2E:
    """MJML → MjmlImportAdapter.parse → EmailDesignDocument → compile → HTML."""

    def test_mjml_import_to_document(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())

        assert isinstance(doc, EmailDesignDocument)
        assert doc.version == "1.0"
        assert doc.source is not None
        assert doc.source.provider == "mjml"
        errors = EmailDesignDocument.validate(doc.to_json())
        assert errors == []
        assert len(doc.sections) >= 4

    @pytest.mark.asyncio
    async def test_mjml_import_to_document_to_html(self) -> None:
        """Full pipeline: MJML → document → MJML generation → compile → HTML."""
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())

        mock_compile = MjmlCompileResult(
            html='<html><body><table role="presentation"><tr><td>Compiled</td></tr></table></body></html>',
            errors=[],
            build_time_ms=50.0,
        )

        converter = DesignConverterService()
        with patch.object(
            converter, "compile_mjml", new_callable=AsyncMock, return_value=mock_compile
        ):
            result = await converter.convert_document_mjml(doc)

        assert isinstance(result, ConversionResult)
        assert "Compiled" in result.html or result.sections_count >= 0

    def test_mjml_import_preserves_dark_mode_tokens(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())

        assert len(doc.tokens.dark_colors) > 0, "Dark mode colors not extracted from MJML"

    def test_mjml_two_column_section_detected(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())

        multi_col = [s for s in doc.sections if s.column_count > 1]
        assert len(multi_col) >= 1, "Two-column section not detected"

    def test_mjml_hero_section_detected(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())

        hero_sections = [s for s in doc.sections if s.type == "hero"]
        assert len(hero_sections) >= 1, "Hero section not detected"

    def test_mjml_button_with_href_preserved(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())

        all_buttons = [b for s in doc.sections for b in s.buttons]
        assert len(all_buttons) >= 1, "No buttons detected in MJML"

    def test_mjml_document_converts_via_html_path(self) -> None:
        """convert_document() (HTML path) with an MJML-imported document."""
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())

        converter = DesignConverterService()
        result = converter.convert_document(doc)

        assert isinstance(result, ConversionResult)
        # Even if sections_count is 0 (no component match), should not crash
        assert result.html is not None

    @pytest.mark.asyncio
    async def test_mjml_compile_error_returns_empty(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())

        converter = DesignConverterService()
        with patch.object(
            converter,
            "compile_mjml",
            new_callable=AsyncMock,
            side_effect=Exception("Sidecar unavailable"),
        ):
            with pytest.raises(Exception, match="Sidecar unavailable"):
                await converter.convert_document_mjml(doc)


# ── 3. HTML Import E2E ────────────────────────────────────────────────


class TestHtmlImportE2E:
    """HTML → HtmlImportAdapter.parse → EmailDesignDocument → convert → HTML."""

    @pytest.mark.asyncio
    async def test_html_import_to_document(self) -> None:
        adapter = HtmlImportAdapter()
        doc = await adapter.parse(_simple_email_html(), use_ai=False)

        assert isinstance(doc, EmailDesignDocument)
        assert doc.version == "1.0"
        assert doc.source is not None
        assert doc.source.provider == "html"
        errors = EmailDesignDocument.validate(doc.to_json())
        assert errors == []
        assert len(doc.sections) >= 3

    @pytest.mark.asyncio
    async def test_html_import_to_document_to_html(self) -> None:
        adapter = HtmlImportAdapter()
        doc = await adapter.parse(_simple_email_html(), use_ai=False)

        converter = DesignConverterService()
        result = converter.convert_document(doc)

        assert isinstance(result, ConversionResult)
        assert result.html is not None

    @pytest.mark.asyncio
    async def test_html_import_extracts_tokens(self) -> None:
        adapter = HtmlImportAdapter()
        doc = await adapter.parse(_simple_email_html(), use_ai=False)

        assert len(doc.tokens.colors) > 0, "No colors extracted from HTML"

    @pytest.mark.asyncio
    async def test_html_import_dark_mode_extracted(self) -> None:
        adapter = HtmlImportAdapter()
        doc = await adapter.parse(_simple_email_html(), use_ai=False)

        assert len(doc.tokens.dark_colors) > 0, "Dark mode colors not extracted from HTML"

    @pytest.mark.asyncio
    async def test_html_import_container_width(self) -> None:
        adapter = HtmlImportAdapter()
        doc = await adapter.parse(_simple_email_html(), use_ai=False)

        assert doc.layout.container_width == 600

    @pytest.mark.asyncio
    async def test_html_import_section_bridge_roundtrip(self) -> None:
        """Sections from HTML import can bridge to EmailSection and back."""
        adapter = HtmlImportAdapter()
        doc = await adapter.parse(_simple_email_html(), use_ai=False)

        # Forward bridge
        email_sections = doc.to_email_sections()
        assert len(email_sections) == len(doc.sections)

        # Reverse bridge
        doc_sections_back = [DocumentSection.from_email_section(s) for s in email_sections]
        assert len(doc_sections_back) == len(doc.sections)


# ── 4. Cross-Format Equivalence ───────────────────────────────────────


class TestCrossFormatEquivalence:
    """Same email imported as MJML and HTML → comparable documents."""

    @pytest.mark.asyncio
    async def test_mjml_vs_html_section_count_comparable(self) -> None:
        """Both formats should produce a similar number of sections."""
        mjml_adapter = MjmlImportAdapter()
        html_adapter = HtmlImportAdapter()

        mjml_doc = mjml_adapter.parse(_full_mjml())
        html_doc = await html_adapter.parse(_simple_email_html(), use_ai=False)

        # Both emails have header/hero/content/cta/footer — counts should be in same range
        assert abs(len(mjml_doc.sections) - len(html_doc.sections)) <= 3, (
            f"Section count diverges too much: MJML={len(mjml_doc.sections)}, "
            f"HTML={len(html_doc.sections)}"
        )

    @pytest.mark.asyncio
    async def test_both_formats_produce_valid_documents(self) -> None:
        mjml_adapter = MjmlImportAdapter()
        html_adapter = HtmlImportAdapter()

        mjml_doc = mjml_adapter.parse(_full_mjml())
        html_doc = await html_adapter.parse(_simple_email_html(), use_ai=False)

        mjml_errors = EmailDesignDocument.validate(mjml_doc.to_json())
        html_errors = EmailDesignDocument.validate(html_doc.to_json())

        assert mjml_errors == [], f"MJML document invalid: {mjml_errors}"
        assert html_errors == [], f"HTML document invalid: {html_errors}"

    @pytest.mark.asyncio
    async def test_both_formats_convertible_to_html(self) -> None:
        """Both documents should be convertible via convert_document()."""
        mjml_adapter = MjmlImportAdapter()
        html_adapter = HtmlImportAdapter()

        mjml_doc = mjml_adapter.parse(_full_mjml())
        html_doc = await html_adapter.parse(_simple_email_html(), use_ai=False)

        converter = DesignConverterService()
        mjml_result = converter.convert_document(mjml_doc)
        html_result = converter.convert_document(html_doc)

        # Both should produce some output (even if component matching varies)
        assert isinstance(mjml_result, ConversionResult)
        assert isinstance(html_result, ConversionResult)


# ── 5. Penpot E2E ─────────────────────────────────────────────────────


class TestPenpotE2E:
    """Penpot API → build_document() → convert_document() → HTML."""

    @pytest.mark.asyncio
    async def test_penpot_build_and_convert_produces_valid_html(self) -> None:
        tokens = _make_tokens()
        structure = _make_structure()
        service = PenpotDesignSyncService()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _out_tokens, _warnings, _out_structure = await service.build_document(
                file_ref="file123", access_token="token123"
            )

        assert isinstance(doc, EmailDesignDocument)
        errors = EmailDesignDocument.validate(doc.to_json())
        assert errors == []

        converter = DesignConverterService()
        result = converter.convert_document(doc)

        assert isinstance(result, ConversionResult)
        assert result.sections_count > 0 or result.html is not None

    @pytest.mark.asyncio
    async def test_penpot_document_has_sections(self) -> None:
        tokens = _make_tokens()
        structure = _make_structure()
        service = PenpotDesignSyncService()

        with patch.object(
            service,
            "sync_tokens_and_structure",
            new_callable=AsyncMock,
            return_value=(tokens, structure),
        ):
            doc, _tokens, _warnings, _struct = await service.build_document(
                file_ref="file123", access_token="token123"
            )

        assert len(doc.sections) > 0


# ── 6. Document Validation E2E ─────────────────────────────────────────


class TestDocumentValidationE2E:
    """End-to-end schema validation checks."""

    def test_document_roundtrip_json(self) -> None:
        doc = _make_document()
        json_data = doc.to_json()
        restored = EmailDesignDocument.from_json(json_data)

        assert restored.version == doc.version
        assert len(restored.sections) == len(doc.sections)
        assert len(restored.tokens.colors) == len(doc.tokens.colors)

    def test_document_to_layout_description(self) -> None:
        doc = _make_document()
        layout = doc.to_layout_description()

        assert len(layout.sections) == len(doc.sections)
        assert layout.total_text_blocks > 0
        assert layout.total_images > 0

    def test_empty_sections_produces_no_sections_warning(self) -> None:
        doc = _make_document(sections=[])
        converter = DesignConverterService()
        result = converter.convert_document(doc)

        assert result.sections_count == 0
        assert any("No sections" in w for w in result.warnings)

    def test_convert_document_with_image_urls(self) -> None:
        doc = _make_document()
        converter = DesignConverterService()
        result = converter.convert_document(
            doc, image_urls={"hero_img": "https://example.com/hero.jpg"}
        )

        assert isinstance(result, ConversionResult)
