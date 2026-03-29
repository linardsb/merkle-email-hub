"""Tests for MJML Import Adapter (Phase 36.4)."""

from __future__ import annotations

from typing import Any

import pytest

from app.design_sync.exceptions import MjmlImportError
from app.design_sync.mjml_import.adapter import MjmlImportAdapter
from app.design_sync.mjml_import.section_parser import (
    _parse_padding,
    parse_sections,
)
from app.design_sync.mjml_import.token_extractor import extract_tokens
from app.design_sync.mjml_import.type_inferrer import infer_section_types

# ── Factories ────────────────────────────────────────────────────────


def _minimal_mjml() -> str:
    return (
        "<mjml><mj-body>"
        "<mj-section><mj-column>"
        "<mj-text>Hello</mj-text>"
        "</mj-column></mj-section>"
        "</mj-body></mjml>"
    )


def _full_mjml() -> str:
    return """\
<mjml>
  <mj-head>
    <mj-attributes>
      <mj-all font-family="Inter" font-size="16px" color="#333333" />
      <mj-text font-family="Georgia" font-size="14px" />
      <mj-button background-color="#FF6600" color="#FFFFFF" font-size="18px" />
    </mj-attributes>
    <mj-style>
      :root { --brand-primary: #FF6600; --brand-bg: #F5F5F5; }
      @media (prefers-color-scheme: dark) {
        .dark-bg { background-color: #1A1A1A; }
        .dark-text { color: #EEEEEE; }
      }
    </mj-style>
    <mj-font name="Roboto" href="https://fonts.googleapis.com/css?family=Roboto" />
  </mj-head>
  <mj-body width="700px">
    <mj-section padding="10px 20px">
      <mj-column>
        <mj-image src="https://example.com/logo.png" alt="Logo" width="150px" />
      </mj-column>
    </mj-section>
    <mj-hero background-url="https://example.com/hero.jpg" background-color="#FF6600" padding="30px">
      <mj-column>
        <mj-text font-size="32px" font-weight="700"><h1>Big Headline</h1></mj-text>
        <mj-text>Body text under hero</mj-text>
      </mj-column>
    </mj-hero>
    <mj-section padding="20px">
      <mj-column width="50%">
        <mj-text><h2>Col 1 Title</h2></mj-text>
        <mj-image src="https://example.com/img1.png" alt="Image 1" width="250px" />
      </mj-column>
      <mj-column width="50%">
        <mj-text><h2>Col 2 Title</h2></mj-text>
        <mj-image src="https://example.com/img2.png" alt="Image 2" width="250px" />
      </mj-column>
    </mj-section>
    <mj-section>
      <mj-column>
        <mj-button href="https://example.com/cta">Click Here</mj-button>
      </mj-column>
    </mj-section>
    <mj-section padding="10px">
      <mj-column>
        <mj-text font-size="12px">Copyright 2026 Example Inc.</mj-text>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>"""


def _parse_head(mjml: str) -> Any:
    from lxml import etree

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(mjml.encode(), parser=parser)
    return root.find("mj-head")


def _parse_body(mjml: str) -> Any:
    from lxml import etree

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(mjml.encode(), parser=parser)
    return root.find("mj-body")


# ── TestMjmlXmlParsing ──────────────────────────────────────────────


class TestMjmlXmlParsing:
    """XML parsing, validation, and security tests."""

    def test_valid_xml(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_minimal_mjml())
        assert doc.version == "1.0"
        assert doc.source is not None
        assert doc.source.provider == "mjml"

    def test_malformed_xml(self) -> None:
        adapter = MjmlImportAdapter()
        with pytest.raises(MjmlImportError, match="not well-formed"):
            adapter.parse("<mjml><mj-body><unclosed>")

    def test_xxe_payload_rejected(self) -> None:
        xxe = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            "<mjml><mj-body><mj-section><mj-column>"
            "<mj-text>&xxe;</mj-text>"
            "</mj-column></mj-section></mj-body></mjml>"
        )
        adapter = MjmlImportAdapter()
        # lxml with resolve_entities=False raises on undefined entity refs
        # or silently drops them — either way, /etc/passwd is not in output
        try:
            doc = adapter.parse(xxe)
            # If it parsed, verify entity was NOT expanded
            for section in doc.sections:
                for text in section.texts:
                    assert "root:" not in text.content
        except MjmlImportError:
            pass  # Also acceptable — malformed XML due to entity

    def test_non_mjml_root_rejected(self) -> None:
        adapter = MjmlImportAdapter()
        with pytest.raises(MjmlImportError, match="Root element must be <mjml>"):
            adapter.parse("<html><body>Not MJML</body></html>")

    def test_missing_mj_body(self) -> None:
        adapter = MjmlImportAdapter()
        with pytest.raises(MjmlImportError, match="Missing <mj-body>"):
            adapter.parse("<mjml><mj-head></mj-head></mjml>")

    def test_size_limit_exceeded(self) -> None:
        # 2 MB + 1 byte
        huge = "<mjml><mj-body>" + "x" * (2 * 1024 * 1024) + "</mj-body></mjml>"
        adapter = MjmlImportAdapter()
        with pytest.raises(MjmlImportError, match="2 MB"):
            adapter.parse(huge)


# ── TestTokenExtraction ─────────────────────────────────────────────


class TestTokenExtraction:
    """Token extraction from <mj-head>."""

    def test_mj_all_default_typography(self) -> None:
        head = _parse_head(_full_mjml())
        tokens = extract_tokens(head)
        names = [t.name for t in tokens.typography]
        assert "all" in names
        all_typo = next(t for t in tokens.typography if t.name == "all")
        assert all_typo.family == "Inter"
        assert all_typo.size == 16.0

    def test_mj_text_overrides(self) -> None:
        head = _parse_head(_full_mjml())
        tokens = extract_tokens(head)
        text_typo = next(t for t in tokens.typography if t.name == "text")
        assert text_typo.family == "Georgia"
        assert text_typo.size == 14.0

    def test_mj_button_defaults(self) -> None:
        head = _parse_head(_full_mjml())
        tokens = extract_tokens(head)
        btn_typo = next(t for t in tokens.typography if t.name == "button")
        assert btn_typo.size == 18.0
        assert btn_typo.family == "inherit"  # No font-family on mj-button in test MJML

    def test_css_color_variables(self) -> None:
        head = _parse_head(_full_mjml())
        tokens = extract_tokens(head)
        color_names = [c.name for c in tokens.colors]
        # brand-bg is extracted; brand-primary (#FF6600) is deduplicated
        # because mj-button-bg already captured the same hex
        assert "brand-bg" in color_names
        bg = next(c for c in tokens.colors if c.name == "brand-bg")
        assert bg.hex == "#F5F5F5"

    def test_dark_mode_colors(self) -> None:
        head = _parse_head(_full_mjml())
        tokens = extract_tokens(head)
        assert len(tokens.dark_colors) >= 1
        dark_names = [c.name for c in tokens.dark_colors]
        assert "dark-background-color" in dark_names

    def test_mj_font_web_fonts(self) -> None:
        head = _parse_head(_full_mjml())
        tokens = extract_tokens(head)
        font_names = [t.name for t in tokens.typography]
        assert "font-Roboto" in font_names

    def test_empty_head_returns_empty_tokens(self) -> None:
        tokens = extract_tokens(None)
        assert tokens.colors == []
        assert tokens.typography == []
        assert tokens.dark_colors == []


# ── TestSectionParsing ──────────────────────────────────────────────


class TestSectionParsing:
    """Section parsing from <mj-body>."""

    def test_single_section(self) -> None:
        body = _parse_body(_minimal_mjml())
        assert body is not None
        sections = parse_sections(body)
        assert len(sections) == 1

    def test_column_layout_single(self) -> None:
        mjml = "<mjml><mj-body><mj-section><mj-column><mj-text>Hi</mj-text></mj-column></mj-section></mj-body></mjml>"
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert sections[0].column_layout == "single"
        assert sections[0].column_count == 1

    def test_column_layout_two_column(self) -> None:
        mjml = (
            "<mjml><mj-body><mj-section>"
            '<mj-column width="50%"><mj-text>A</mj-text></mj-column>'
            '<mj-column width="50%"><mj-text>B</mj-text></mj-column>'
            "</mj-section></mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert sections[0].column_layout == "two-column"
        assert sections[0].column_count == 2
        assert len(sections[0].columns) == 2
        assert sections[0].columns[0].width == 50.0

    def test_text_with_heading(self) -> None:
        mjml = (
            "<mjml><mj-body><mj-section><mj-column>"
            "<mj-text><h1>Title</h1></mj-text>"
            "</mj-column></mj-section></mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert len(sections[0].texts) >= 1
        heading = next(t for t in sections[0].texts if t.is_heading)
        assert heading.content == "Title"

    def test_image_element(self) -> None:
        mjml = (
            "<mjml><mj-body><mj-section><mj-column>"
            '<mj-image src="https://example.com/img.png" alt="Test" width="300px" />'
            "</mj-column></mj-section></mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert len(sections[0].images) == 1
        img = sections[0].images[0]
        assert img.node_name == "Test"
        assert img.width == 300.0

    def test_button_element(self) -> None:
        mjml = (
            "<mjml><mj-body><mj-section><mj-column>"
            '<mj-button href="https://example.com">Click</mj-button>'
            "</mj-column></mj-section></mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert len(sections[0].buttons) == 1
        assert sections[0].buttons[0].text == "Click"

    def test_spacer_section(self) -> None:
        mjml = (
            '<mjml><mj-body><mj-section><mj-spacer height="40px" /></mj-section></mj-body></mjml>'
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert sections[0].type == "spacer"
        assert sections[0].height == 40.0

    def test_divider_section(self) -> None:
        mjml = (
            "<mjml><mj-body>"
            '<mj-section><mj-divider border-color="#cccccc" /></mj-section>'
            "</mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert sections[0].type == "divider"

    def test_hero_section(self) -> None:
        mjml = (
            "<mjml><mj-body>"
            '<mj-hero background-url="https://example.com/bg.jpg" background-color="#FF0000">'
            "<mj-column><mj-text><h1>Hero Title</h1></mj-text></mj-column>"
            "</mj-hero>"
            "</mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert sections[0].type == "hero"
        bg_images = [i for i in sections[0].images if i.is_background]
        assert len(bg_images) == 1

    def test_social_section(self) -> None:
        mjml = (
            "<mjml><mj-body>"
            "<mj-section>"
            '<mj-social><mj-social-element name="facebook" src="https://example.com/fb.png" /></mj-social>'
            "</mj-section>"
            "</mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert sections[0].type == "social"
        assert "social_links" in sections[0].content_roles

    def test_navbar_section(self) -> None:
        mjml = (
            "<mjml><mj-body>"
            "<mj-section>"
            "<mj-navbar>"
            "<mj-navbar-link>Home</mj-navbar-link>"
            "<mj-navbar-link>About</mj-navbar-link>"
            "</mj-navbar>"
            "</mj-section>"
            "</mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert sections[0].type == "nav"
        assert len(sections[0].texts) == 2

    def test_padding_shorthand_1_value(self) -> None:
        pad = _parse_padding("10px")
        assert pad is not None
        assert pad.top == 10.0
        assert pad.right == 10.0

    def test_padding_shorthand_2_values(self) -> None:
        pad = _parse_padding("10px 20px")
        assert pad is not None
        assert pad.top == 10.0
        assert pad.right == 20.0
        assert pad.bottom == 10.0
        assert pad.left == 20.0

    def test_padding_shorthand_4_values(self) -> None:
        pad = _parse_padding("10px 20px 30px 40px")
        assert pad is not None
        assert pad.top == 10.0
        assert pad.right == 20.0
        assert pad.bottom == 30.0
        assert pad.left == 40.0

    def test_javascript_url_rejected(self) -> None:
        mjml = (
            "<mjml><mj-body><mj-section><mj-column>"
            '<mj-image src="javascript:alert(1)" alt="xss" />'
            "</mj-column></mj-section></mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert len(sections[0].images) == 0

    def test_wrapper_unwrapped(self) -> None:
        mjml = (
            "<mjml><mj-body>"
            "<mj-wrapper>"
            "<mj-section><mj-column><mj-text>Inside wrapper</mj-text></mj-column></mj-section>"
            "</mj-wrapper>"
            "</mj-body></mjml>"
        )
        body = _parse_body(mjml)
        assert body is not None
        sections = parse_sections(body)
        assert len(sections) == 1
        assert sections[0].texts[0].content == "Inside wrapper"


# ── TestTypeInference ───────────────────────────────────────────────


class TestTypeInference:
    """Section type inference heuristics."""

    def test_first_image_only_is_header(self) -> None:
        from app.design_sync.email_design_document import DocumentImage, DocumentSection

        sections = [
            DocumentSection(
                id="s1",
                type="unknown",
                images=[DocumentImage(node_id="i1", node_name="logo")],
            ),
            DocumentSection(id="s2", type="unknown"),
        ]
        result = infer_section_types(sections)
        assert result[0].type == "header"

    def test_last_small_text_is_footer(self) -> None:
        from app.design_sync.email_design_document import DocumentSection, DocumentText

        sections = [
            DocumentSection(id="s1", type="unknown"),
            DocumentSection(
                id="s2",
                type="unknown",
                texts=[DocumentText(node_id="t1", content="(c) 2026", font_size=11.0)],
            ),
        ]
        result = infer_section_types(sections)
        assert result[1].type == "footer"

    def test_button_only_is_cta(self) -> None:
        from app.design_sync.email_design_document import DocumentButton, DocumentSection

        sections = [
            DocumentSection(id="s0", type="unknown"),
            DocumentSection(
                id="s1",
                type="unknown",
                buttons=[DocumentButton(node_id="b1", text="Buy Now")],
            ),
            DocumentSection(id="s2", type="unknown"),
        ]
        result = infer_section_types(sections)
        assert result[1].type == "cta"

    def test_explicit_types_preserved(self) -> None:
        from app.design_sync.email_design_document import DocumentSection

        sections = [
            DocumentSection(id="s1", type="hero"),
            DocumentSection(id="s2", type="social"),
            DocumentSection(id="s3", type="nav"),
            DocumentSection(id="s4", type="spacer"),
            DocumentSection(id="s5", type="divider"),
        ]
        result = infer_section_types(sections)
        assert [s.type for s in result] == ["hero", "social", "nav", "spacer", "divider"]

    def test_mixed_content_is_content(self) -> None:
        from app.design_sync.email_design_document import (
            DocumentImage,
            DocumentSection,
            DocumentText,
        )

        sections = [
            DocumentSection(id="s0", type="content"),
            DocumentSection(
                id="s1",
                type="unknown",
                texts=[DocumentText(node_id="t1", content="Article body", font_size=16.0)],
                images=[DocumentImage(node_id="i1", node_name="photo")],
            ),
            DocumentSection(id="s2", type="content"),
        ]
        result = infer_section_types(sections)
        assert result[1].type == "content"


# ── TestAdapterIntegration ──────────────────────────────────────────


class TestAdapterIntegration:
    """End-to-end adapter tests."""

    def test_minimal_roundtrip(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_minimal_mjml())
        assert doc.version == "1.0"
        assert doc.source is not None
        assert doc.source.provider == "mjml"
        assert len(doc.sections) == 1

    def test_full_mjml_all_section_types(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())
        types = [s.type for s in doc.sections]
        assert "hero" in types
        # Footer inferred from last section with small text
        assert types[-1] == "footer"
        assert len(doc.sections) >= 4

    def test_container_width_from_body(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())
        assert doc.layout.container_width == 700

    def test_default_container_width(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_minimal_mjml())
        assert doc.layout.container_width == 600

    def test_provider_is_mjml(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_minimal_mjml())
        assert doc.source is not None
        assert doc.source.provider == "mjml"

    def test_naming_convention_is_mjml(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_minimal_mjml())
        assert doc.layout.naming_convention == "mjml"

    def test_document_validates_against_schema(self) -> None:
        from app.design_sync.email_design_document import EmailDesignDocument

        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())
        doc_json = doc.to_json()
        errors = EmailDesignDocument.validate(doc_json)
        assert not errors, f"Validation errors: {errors}"

    def test_two_column_section(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())
        two_col = [s for s in doc.sections if s.column_layout == "two-column"]
        assert len(two_col) >= 1
        assert two_col[0].column_count == 2
        assert len(two_col[0].columns) == 2

    def test_dark_mode_tokens_extracted(self) -> None:
        adapter = MjmlImportAdapter()
        doc = adapter.parse(_full_mjml())
        assert len(doc.tokens.dark_colors) >= 1

    def test_data_url_image_rejected(self) -> None:
        mjml = (
            "<mjml><mj-body><mj-section><mj-column>"
            '<mj-image src="data:image/png;base64,abc" alt="bad" />'
            "</mj-column></mj-section></mj-body></mjml>"
        )
        adapter = MjmlImportAdapter()
        doc = adapter.parse(mjml)
        assert len(doc.sections[0].images) == 0

    def test_three_column_layout(self) -> None:
        mjml = (
            "<mjml><mj-body><mj-section>"
            '<mj-column width="33%"><mj-text>A</mj-text></mj-column>'
            '<mj-column width="33%"><mj-text>B</mj-text></mj-column>'
            '<mj-column width="33%"><mj-text>C</mj-text></mj-column>'
            "</mj-section></mj-body></mjml>"
        )
        adapter = MjmlImportAdapter()
        doc = adapter.parse(mjml)
        assert doc.sections[0].column_layout == "three-column"
        assert doc.sections[0].column_count == 3
