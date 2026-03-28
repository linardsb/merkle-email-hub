"""Tests for token_extractor module."""

from __future__ import annotations

from pathlib import Path

from app.design_sync.email_design_document import DocumentPadding, DocumentSection, DocumentText
from app.design_sync.html_import.dom_parser import parse_email_dom
from app.design_sync.html_import.token_extractor import (
    detect_web_fonts,
    extract_tokens,
)

_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "ai" / "templates" / "library"


def _make_section(
    section_id: str = "s1",
    bg_color: str | None = None,
    texts: list[DocumentText] | None = None,
    padding: DocumentPadding | None = None,
) -> DocumentSection:
    return DocumentSection(
        id=section_id,
        type="content",
        background_color=bg_color,
        texts=texts or [],
        padding=padding,
    )


def _make_text(
    content: str = "Hello",
    font_family: str | None = "Arial",
    font_size: float | None = 16.0,
    font_weight: int | None = 400,
) -> DocumentText:
    return DocumentText(
        node_id="t1",
        content=content,
        font_family=font_family,
        font_size=font_size,
        font_weight=font_weight,
    )


class TestExtractTokens:
    def test_empty_inputs(self) -> None:
        tokens = extract_tokens([], [])
        assert tokens.colors == []
        assert tokens.typography == []
        assert tokens.spacing == []

    def test_color_deduplication(self) -> None:
        sections = [
            _make_section(bg_color="#ff5500"),
            _make_section(section_id="s2", bg_color="#ff5500"),
            _make_section(section_id="s3", bg_color="#333333"),
        ]
        tokens = extract_tokens([], sections)
        hex_values = {c.hex for c in tokens.colors}
        assert "#ff5500" in hex_values
        assert "#333333" in hex_values

    def test_color_role_assignment(self) -> None:
        sections = [
            _make_section(bg_color="#ffffff"),
            _make_section(section_id="s2", bg_color="#ffffff"),
        ]
        tokens = extract_tokens([], sections)
        roles = {c.name for c in tokens.colors}
        assert "background" in roles

    def test_typography_extraction(self) -> None:
        sections = [
            _make_section(
                texts=[
                    _make_text(font_family="Inter", font_size=32.0, font_weight=700),
                    _make_text(font_family="Inter", font_size=16.0, font_weight=400),
                ]
            ),
        ]
        tokens = extract_tokens([], sections)
        assert len(tokens.typography) >= 2
        names = {t.name for t in tokens.typography}
        assert "heading" in names
        assert "body" in names

    def test_heading_vs_body_detection(self) -> None:
        sections = [
            _make_section(
                texts=[
                    _make_text(font_size=28.0),
                    _make_text(font_size=14.0),
                ]
            ),
        ]
        tokens = extract_tokens([], sections)
        heading = next((t for t in tokens.typography if t.name == "heading"), None)
        body = next((t for t in tokens.typography if t.name == "body"), None)
        assert heading is not None
        assert heading.size >= 20.0
        assert body is not None
        assert body.size < 20.0

    def test_spacing_extraction(self) -> None:
        sections = [
            _make_section(padding=DocumentPadding(top=10.0, right=20.0, bottom=10.0, left=20.0)),
            _make_section(
                section_id="s2",
                padding=DocumentPadding(top=30.0, right=20.0, bottom=30.0, left=20.0),
            ),
        ]
        tokens = extract_tokens([], sections)
        assert len(tokens.spacing) >= 2
        values = {s.value for s in tokens.spacing}
        assert 10.0 in values
        assert 20.0 in values

    def test_dark_mode_extraction(self) -> None:
        css = """
        @media (prefers-color-scheme: dark) {
            .dark-bg { background-color: #1a1a2e !important; }
            .dark-text { color: #e5e5e5 !important; }
        }
        """
        tokens = extract_tokens([css], [])
        assert len(tokens.dark_colors) >= 1
        hex_values = {c.hex for c in tokens.dark_colors}
        assert "#1a1a2e" in hex_values or "#e5e5e5" in hex_values

    def test_css_colors_from_style_blocks(self) -> None:
        css = "body { color: #333333; } a { color: #0066cc; }"
        tokens = extract_tokens([css], [])
        hex_values = {c.hex for c in tokens.colors}
        assert "#333333" in hex_values
        assert "#0066cc" in hex_values

    def test_empty_style_blocks_minimal_tokens(self) -> None:
        tokens = extract_tokens([], [_make_section()])
        # Should not crash, may have empty tokens
        assert isinstance(tokens.colors, list)


class TestDetectWebFonts:
    def test_import_url(self) -> None:
        css = "@import url('https://fonts.googleapis.com/css2?family=Inter');"
        fonts = detect_web_fonts([css])
        assert len(fonts) >= 1
        assert "fonts.googleapis.com" in fonts[0]

    def test_font_face(self) -> None:
        css = """
        @font-face {
            font-family: 'CustomFont';
            src: url('https://example.com/font.woff2') format('woff2');
        }
        """
        fonts = detect_web_fonts([css])
        assert len(fonts) >= 1

    def test_no_fonts(self) -> None:
        fonts = detect_web_fonts(["body { color: red; }"])
        assert fonts == []

    def test_deduplication(self) -> None:
        css = "@import url('https://fonts.com/a'); @import url('https://fonts.com/a');"
        fonts = detect_web_fonts([css])
        assert len(fonts) == 1


class TestGoldenTemplateTokens:
    def test_promotional_hero_tokens(self) -> None:
        html = (_TEMPLATE_DIR / "promotional_hero.html").read_text()
        parsed = parse_email_dom(html)
        tokens = extract_tokens(parsed.style_blocks, parsed.sections)
        assert len(tokens.colors) >= 1
        assert len(tokens.typography) >= 1
