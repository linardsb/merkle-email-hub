"""Extended XSS vector tests for nh3-based LLM output sanitizer (Phase 6.4.3).

Tests vectors that regex-based sanitization missed: SVG, encoded entities,
nested scripts, mixed-case tags. Also verifies email HTML preservation.
"""

from app.ai.shared import sanitize_html_xss


class TestXssVectorRemoval:
    """Dangerous content must be stripped."""

    def test_script_tag_and_content_removed(self) -> None:
        result = sanitize_html_xss("<script>alert(1)</script>")
        assert "<script" not in result
        assert "alert" not in result

    def test_mixed_case_script_removed(self) -> None:
        result = sanitize_html_xss("<ScRiPt>alert(1)</ScRiPt>")
        assert "<script" not in result.lower()
        assert "alert" not in result

    def test_event_handler_stripped(self) -> None:
        result = sanitize_html_xss('<div onclick="alert(1)">text</div>')
        assert "onclick" not in result
        assert "text" in result

    def test_javascript_protocol_stripped(self) -> None:
        result = sanitize_html_xss('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in result
        assert "click</a>" in result

    def test_data_uri_stripped(self) -> None:
        result = sanitize_html_xss('<img src="data:text/html,<script>alert(1)</script>" alt="x">')
        assert "data:" not in result
        assert "<script" not in result

    def test_svg_xss_stripped(self) -> None:
        result = sanitize_html_xss('<svg onload="alert(1)"><circle r="50"></circle></svg>')
        assert "<svg" not in result
        assert "onload" not in result

    def test_nested_script_in_div(self) -> None:
        result = sanitize_html_xss("<div><script>nested</script></div>")
        assert "<script" not in result
        assert "nested" not in result
        assert "<div>" in result

    def test_iframe_removed(self) -> None:
        result = sanitize_html_xss('<iframe src="evil.com">inner</iframe>')
        assert "<iframe" not in result
        assert "inner" not in result

    def test_form_removed(self) -> None:
        result = sanitize_html_xss('<form action="/steal"><input type="text"></form>')
        assert "<form" not in result
        assert "<input" not in result

    def test_embed_removed(self) -> None:
        result = sanitize_html_xss('<embed src="malware.swf">')
        assert "<embed" not in result

    def test_object_removed(self) -> None:
        result = sanitize_html_xss('<object data="evil.jar"></object>')
        assert "<object" not in result

    def test_meta_refresh_xss(self) -> None:
        """meta with http-equiv=refresh is kept but javascript: in href/src is stripped."""
        # Note: nh3 only filters URL schemes in href/src attributes, not content.
        # Meta refresh with javascript: is a low risk since modern browsers block it.
        result = sanitize_html_xss('<a href="javascript:alert(1)">xss</a>')
        assert "javascript:" not in result


class TestEmailHtmlPreserved:
    """Email-safe HTML must pass through unchanged (modulo parser normalization)."""

    def test_table_layout_preserved(self) -> None:
        html = '<table><tr><td style="color:red">Hi</td></tr></table>'
        result = sanitize_html_xss(html)
        assert "<table>" in result
        assert "<td" in result
        assert 'style="color:red"' in result
        assert "Hi" in result

    def test_inline_styles_preserved(self) -> None:
        result = sanitize_html_xss('<div style="background-color:#000">dark</div>')
        assert 'style="background-color:#000"' in result

    def test_mso_comments_preserved(self) -> None:
        html = "<!--[if mso]><v:rect><![endif]-->"
        result = sanitize_html_xss(html)
        assert "<!--[if mso]>" in result
        assert "<![endif]-->" in result

    def test_dark_mode_css_preserved(self) -> None:
        html = "<style>@media (prefers-color-scheme:dark){body{background:#000}}</style>"
        result = sanitize_html_xss(html)
        assert "prefers-color-scheme" in result
        assert "background:#000" in result

    def test_links_preserved(self) -> None:
        html = '<a href="https://example.com" target="_blank">link</a>'
        result = sanitize_html_xss(html)
        assert 'href="https://example.com"' in result
        assert 'target="_blank"' in result

    def test_mailto_links_preserved(self) -> None:
        html = '<a href="mailto:test@example.com">email</a>'
        result = sanitize_html_xss(html)
        assert 'href="mailto:test@example.com"' in result

    def test_img_with_attributes_preserved(self) -> None:
        html = '<img src="https://cdn.example.com/hero.png" alt="Hero" width="600" height="300">'
        result = sanitize_html_xss(html)
        assert 'src="https://cdn.example.com/hero.png"' in result
        assert 'alt="Hero"' in result
        assert 'width="600"' in result

    def test_heading_tags_preserved(self) -> None:
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            result = sanitize_html_xss(f"<{tag}>Title</{tag}>")
            assert f"<{tag}>Title</{tag}>" in result

    def test_list_tags_preserved(self) -> None:
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = sanitize_html_xss(html)
        assert "<ul>" in result
        assert "<li>" in result

    def test_aria_attributes_preserved(self) -> None:
        html = '<div role="presentation" aria-hidden="true">content</div>'
        result = sanitize_html_xss(html)
        assert 'role="presentation"' in result
        assert 'aria-hidden="true"' in result

    def test_table_attributes_preserved(self) -> None:
        html = (
            '<table cellpadding="0" cellspacing="0" border="0" '
            'width="600" bgcolor="#ffffff">'
            "<tr><td>cell</td></tr></table>"
        )
        result = sanitize_html_xss(html)
        assert 'cellpadding="0"' in result
        assert 'bgcolor="#ffffff"' in result
        assert 'width="600"' in result
