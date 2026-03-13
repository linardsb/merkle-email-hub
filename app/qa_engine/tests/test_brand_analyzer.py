"""Unit tests for brand compliance analyzer."""

from lxml import html as lxml_html

from app.qa_engine.brand_analyzer import (
    analyze_brand,
    clear_brand_cache,
    detect_required_elements,
    extract_colors,
    extract_fonts,
)


class TestExtractColors:
    def test_hex_colors(self) -> None:
        html = "<html><head><style>p { color: #ff0000; background-color: #003366; }</style></head><body><p>Test</p></body></html>"
        doc = lxml_html.document_fromstring(html)
        colors = extract_colors(doc, html)
        assert "#ff0000" in colors
        assert "#003366" in colors

    def test_inline_style_colors(self) -> None:
        html = '<html><body><p style="color: #abc;">Test</p></body></html>'
        doc = lxml_html.document_fromstring(html)
        colors = extract_colors(doc, html)
        assert "#aabbcc" in colors  # 3-char hex expanded

    def test_rgb_colors(self) -> None:
        html = "<html><head><style>p { color: rgb(255, 0, 0); }</style></head><body><p>Test</p></body></html>"
        doc = lxml_html.document_fromstring(html)
        colors = extract_colors(doc, html)
        assert any("rgb" in c for c in colors)

    def test_named_colors(self) -> None:
        html = "<html><head><style>p { color: red; background: white; }</style></head><body><p>Test</p></body></html>"
        doc = lxml_html.document_fromstring(html)
        colors = extract_colors(doc, html)
        assert "red" in colors
        assert "white" in colors

    def test_no_colors(self) -> None:
        html = "<html><body><p>No styles</p></body></html>"
        doc = lxml_html.document_fromstring(html)
        colors = extract_colors(doc, html)
        assert len(colors) == 0


class TestExtractFonts:
    def test_font_family(self) -> None:
        html = "<html><head><style>body { font-family: Arial, Helvetica, sans-serif; }</style></head><body>Test</body></html>"
        doc = lxml_html.document_fromstring(html)
        fonts = extract_fonts(doc, html)
        assert "arial" in fonts
        assert "helvetica" in fonts
        # sans-serif is included in raw extraction; filtering happens in brand_font_compliance
        assert "sans-serif" in fonts

    def test_quoted_font(self) -> None:
        html = '<html><head><style>p { font-family: "Comic Sans MS"; }</style></head><body><p>Test</p></body></html>'
        doc = lxml_html.document_fromstring(html)
        fonts = extract_fonts(doc, html)
        assert "comic sans ms" in fonts


class TestDetectElements:
    def test_footer_by_class(self) -> None:
        html = '<html><body><div class="email-footer">Legal</div></body></html>'
        doc = lxml_html.document_fromstring(html)
        has_footer, _, _ = detect_required_elements(doc, html)
        assert has_footer is True

    def test_footer_by_tag(self) -> None:
        html = "<html><body><footer>Legal</footer></body></html>"
        doc = lxml_html.document_fromstring(html)
        has_footer, _, _ = detect_required_elements(doc, html)
        assert has_footer is True

    def test_no_footer(self) -> None:
        html = "<html><body><p>No footer</p></body></html>"
        doc = lxml_html.document_fromstring(html)
        has_footer, _, _ = detect_required_elements(doc, html)
        assert has_footer is False

    def test_logo_by_alt(self) -> None:
        html = "<html><body><img alt='Company Logo' src='img.png'></body></html>"
        doc = lxml_html.document_fromstring(html)
        _, has_logo, _ = detect_required_elements(doc, html)
        assert has_logo is True

    def test_logo_by_src(self) -> None:
        html = "<html><body><img alt='' src='logo.png'></body></html>"
        doc = lxml_html.document_fromstring(html)
        _, has_logo, _ = detect_required_elements(doc, html)
        assert has_logo is True

    def test_unsubscribe_by_text(self) -> None:
        html = '<html><body><a href="https://example.com/unsub">Unsubscribe</a></body></html>'
        doc = lxml_html.document_fromstring(html)
        _, _, has_unsub = detect_required_elements(doc, html)
        assert has_unsub is True

    def test_unsubscribe_by_href(self) -> None:
        html = '<html><body><a href="https://example.com/unsubscribe">Click</a></body></html>'
        doc = lxml_html.document_fromstring(html)
        _, _, has_unsub = detect_required_elements(doc, html)
        assert has_unsub is True


class TestBrandAnalysis:
    def test_caching(self) -> None:
        html = (
            "<html><head><style>p { color: #ff0000; }</style></head><body><p>Test</p></body></html>"
        )
        doc = lxml_html.document_fromstring(html)
        clear_brand_cache()
        a1 = analyze_brand(doc, html)
        a2 = analyze_brand(doc, html)
        assert a1 is a2  # Same cached object
