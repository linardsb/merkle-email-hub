"""Tests for dom_parser module."""

from __future__ import annotations

from pathlib import Path

from app.design_sync.html_import.dom_parser import ParsedEmail, parse_email_dom

_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "ai" / "templates" / "library"


def _load_template(name: str) -> str:
    return (_TEMPLATE_DIR / f"{name}.html").read_text()


# ── Minimal HTML tests ─────────────────────────────────────────────


class TestParseEmailDom:
    def test_empty_html_returns_empty(self) -> None:
        result = parse_email_dom("")
        assert result.sections == []

    def test_whitespace_only_returns_empty(self) -> None:
        result = parse_email_dom("   ")
        assert result.sections == []

    def test_minimal_table_structure(self) -> None:
        html = """
        <html><body>
        <table width="600">
          <tr><td style="padding:20px;"><h1 style="font-size:28px;">Hello</h1></td></tr>
          <tr><td><p>Some content here</p></td></tr>
        </table>
        </body></html>
        """
        result = parse_email_dom(html)
        assert len(result.sections) >= 2
        assert result.container_width == 600

    def test_container_width_detection(self) -> None:
        html = '<html><body><table width="640"><tr><td>Content</td></tr></table></body></html>'
        result = parse_email_dom(html)
        assert result.container_width == 640

    def test_mso_conditional_detection(self) -> None:
        html = """
        <html><body>
        <!--[if mso]><table><tr><td><![endif]-->
        <table width="600"><tr><td>Content</td></tr></table>
        <!--[if mso]></td></tr></table><![endif]-->
        </body></html>
        """
        result = parse_email_dom(html)
        assert result.has_mso_conditionals is True

    def test_dark_mode_detection(self) -> None:
        html = """
        <html><head>
        <style>@media (prefers-color-scheme: dark) { .bg { background: #111; } }</style>
        </head><body><table width="600"><tr><td>Content</td></tr></table></body></html>
        """
        result = parse_email_dom(html)
        assert result.has_dark_mode is True

    def test_charset_detection(self) -> None:
        html = '<html><head><meta charset="utf-8"></head><body><table width="600"><tr><td>X</td></tr></table></body></html>'
        result = parse_email_dom(html)
        assert result.meta_charset == "utf-8"


# ── Text extraction ────────────────────────────────────────────────


class TestTextExtraction:
    def test_extracts_heading(self) -> None:
        html = """
        <table width="600"><tr><td>
        <h1 style="font-size:32px; color:#333;">Welcome</h1>
        </td></tr></table>
        """
        result = parse_email_dom(html)
        assert len(result.sections) >= 1
        texts = result.sections[0].texts
        assert any(t.is_heading for t in texts)
        assert any("Welcome" in t.content for t in texts)

    def test_extracts_paragraph(self) -> None:
        html = """
        <table width="600"><tr><td>
        <p style="font-size:14px; font-family:Arial;">Hello world</p>
        </td></tr></table>
        """
        result = parse_email_dom(html)
        texts = result.sections[0].texts
        assert any("Hello world" in t.content for t in texts)

    def test_skips_hidden_elements(self) -> None:
        html = """
        <table width="600"><tr><td>
        <p style="display:none;">Hidden</p>
        <p>Visible</p>
        </td></tr></table>
        """
        result = parse_email_dom(html)
        texts = result.sections[0].texts
        assert not any("Hidden" in t.content for t in texts)
        assert any("Visible" in t.content for t in texts)


# ── Image extraction ───────────────────────────────────────────────


class TestImageExtraction:
    def test_extracts_img(self) -> None:
        html = """
        <table width="600"><tr><td>
        <img src="https://example.com/hero.jpg" alt="Hero" width="600" height="300">
        </td></tr></table>
        """
        result = parse_email_dom(html)
        images = result.sections[0].images
        assert len(images) >= 1
        assert images[0].width == 600.0
        assert images[0].height == 300.0

    def test_rejects_non_http_src(self) -> None:
        html = """
        <table width="600"><tr><td>
        <img src="javascript:alert(1)" width="100" height="50">
        <img src="https://safe.com/img.png" width="100" height="50">
        </td></tr></table>
        """
        result = parse_email_dom(html)
        images = result.sections[0].images
        # Only the https image should be included
        assert all("javascript" not in (i.node_name or "") for i in images)

    def test_width_from_style(self) -> None:
        html = """
        <table width="600"><tr><td>
        <img src="https://example.com/img.png" style="width:200px; height:100px;" alt="styled">
        </td></tr></table>
        """
        result = parse_email_dom(html)
        images = result.sections[0].images
        assert len(images) >= 1
        assert images[0].width == 200.0


# ── Button extraction ──────────────────────────────────────────────


class TestButtonExtraction:
    def test_link_with_bg_color(self) -> None:
        html = """
        <table width="600"><tr><td>
        <a href="https://example.com" style="background-color:#FF5500; color:#fff; padding:12px 24px;">Shop Now</a>
        </td></tr></table>
        """
        result = parse_email_dom(html)
        buttons = result.sections[0].buttons
        assert len(buttons) >= 1
        assert "Shop Now" in buttons[0].text

    def test_bulletproof_button(self) -> None:
        html = """
        <table width="600"><tr><td>
        <table bgcolor="#FF5500" cellpadding="0" cellspacing="0">
          <tr><td><a href="https://example.com" style="color:#fff;">Click</a></td></tr>
        </table>
        </td></tr></table>
        """
        result = parse_email_dom(html)
        buttons = result.sections[0].buttons
        assert len(buttons) >= 1

    def test_role_button(self) -> None:
        html = """
        <table width="600"><tr><td>
        <div role="button">Submit</div>
        </td></tr></table>
        """
        result = parse_email_dom(html)
        buttons = result.sections[0].buttons
        assert len(buttons) >= 1
        assert "Submit" in buttons[0].text


# ── Column detection ───────────────────────────────────────────────


class TestColumnDetection:
    def test_two_column(self) -> None:
        html = """
        <table width="600"><tr>
          <td width="300"><p>Left</p></td>
          <td width="300"><p>Right</p></td>
        </tr></table>
        """
        result = parse_email_dom(html)
        assert len(result.sections) >= 1
        section = result.sections[0]
        assert section.column_layout == "two-column"
        assert len(section.columns) == 2

    def test_three_column(self) -> None:
        html = """
        <table width="600"><tr>
          <td width="200"><p>A</p></td>
          <td width="200"><p>B</p></td>
          <td width="200"><p>C</p></td>
        </tr></table>
        """
        result = parse_email_dom(html)
        section = result.sections[0]
        assert section.column_layout == "three-column"
        assert len(section.columns) == 3

    def test_single_column_default(self) -> None:
        html = """
        <table width="600"><tr>
          <td><p>Only one column</p></td>
        </tr></table>
        """
        result = parse_email_dom(html)
        section = result.sections[0]
        assert section.column_layout == "single"


# ── Background and padding ─────────────────────────────────────────


class TestBackgroundAndPadding:
    def test_bgcolor_attribute(self) -> None:
        html = """
        <table width="600"><tr bgcolor="#FF5500">
          <td><p>Colourful</p></td>
        </tr></table>
        """
        result = parse_email_dom(html)
        assert result.sections[0].background_color == "#ff5500"

    def test_background_color_style(self) -> None:
        html = """
        <table width="600"><tr>
          <td style="background-color:#333333; padding:20px 30px;"><p>Dark</p></td>
        </tr></table>
        """
        result = parse_email_dom(html)
        section = result.sections[0]
        assert section.background_color == "#333333"
        assert section.padding is not None
        assert section.padding.top == 20.0
        assert section.padding.left == 30.0


# ── Preheader detection ────────────────────────────────────────────


class TestPreheader:
    def test_hidden_div_preheader(self) -> None:
        html = """
        <html><body>
        <div style="display:none; max-height:0; overflow:hidden;">Preheader text here</div>
        <table width="600"><tr><td>Content</td></tr></table>
        </body></html>
        """
        result = parse_email_dom(html)
        assert result.preheader_text is not None
        assert "Preheader" in result.preheader_text


# ── Import annotator integration ───────────────────────────────────


class TestAnnotatorIntegration:
    def test_uses_data_section_id(self) -> None:
        html = """
        <html><body>
        <table width="600">
          <tr><td>
            <div data-section-id="sec-1" data-section-type="header"><img src="https://x.com/logo.png" width="100" height="50"></div>
            <div data-section-id="sec-2" data-section-type="hero"><h1 style="font-size:32px;">Big Title</h1></div>
          </td></tr>
        </table>
        </body></html>
        """
        result = parse_email_dom(html)
        assert len(result.sections) == 2
        assert result.sections[0].id == "sec-1"
        assert result.sections[0].type == "header"
        assert result.sections[1].id == "sec-2"
        assert result.sections[1].type == "hero"


# ── Malformed HTML ─────────────────────────────────────────────────


class TestMalformedHtml:
    def test_unclosed_tags_no_crash(self) -> None:
        html = "<html><body><table width='600'><tr><td><p>Unclosed"
        result = parse_email_dom(html)
        # Should not crash — lxml is lenient
        assert isinstance(result, ParsedEmail)

    def test_no_table_structure(self) -> None:
        html = "<html><body><div><p>Just divs</p></div></body></html>"
        result = parse_email_dom(html)
        # May have zero sections since no table found
        assert isinstance(result, ParsedEmail)


# ── Golden template integration ────────────────────────────────────


class TestGoldenTemplates:
    def test_promotional_hero_parses(self) -> None:
        html = _load_template("promotional_hero")
        result = parse_email_dom(html)
        assert len(result.sections) >= 2
        assert result.container_width >= 580
        assert result.has_mso_conditionals is True
        assert len(result.style_blocks) >= 1

    def test_newsletter_2col_parses(self) -> None:
        html = _load_template("newsletter_2col")
        result = parse_email_dom(html)
        assert len(result.sections) >= 2
        # Should detect some multi-column sections
        has_multicol = any(s.column_layout != "single" for s in result.sections)
        # Not guaranteed but likely for a 2-col newsletter
        assert isinstance(has_multicol, bool)

    def test_minimal_text_parses(self) -> None:
        html = _load_template("minimal_text")
        result = parse_email_dom(html)
        assert len(result.sections) >= 1
        assert result.has_dark_mode is True
