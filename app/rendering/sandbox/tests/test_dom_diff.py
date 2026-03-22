"""Unit tests for DOM diff computation."""

from __future__ import annotations

from app.rendering.sandbox.dom_diff import DOMDiff, _parse_inline_style, compute_dom_diff


class TestParseInlineStyle:
    def test_simple(self) -> None:
        result = _parse_inline_style("color: red; font-size: 14px")
        assert result == {"color": "red", "font-size": "14px"}

    def test_empty(self) -> None:
        assert _parse_inline_style("") == {}

    def test_trailing_semicolon(self) -> None:
        result = _parse_inline_style("margin: 0;")
        assert result == {"margin": "0"}

    def test_mso_properties(self) -> None:
        result = _parse_inline_style(
            "mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse"
        )
        assert result == {
            "mso-table-lspace": "0pt",
            "mso-table-rspace": "0pt",
            "border-collapse": "collapse",
        }


class TestComputeDomDiff:
    def test_identical(self) -> None:
        html = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
            '<tr><td style="color: #333333; font-family: Arial, sans-serif;">Hello</td></tr>'
            "</table>"
        )
        diff = compute_dom_diff(html, html)
        assert diff.removed_elements == []
        assert diff.removed_attributes == {}
        assert diff.removed_css_properties == {}

    def test_removed_style_element(self) -> None:
        original = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
            "<style>td { color: red; }</style>"
            "<tr><td>Hello</td></tr></table>"
        )
        rendered = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
            "<tr><td>Hello</td></tr></table>"
        )
        diff = compute_dom_diff(original, rendered)
        assert "style" in diff.removed_elements

    def test_removed_css_property(self) -> None:
        original = (
            '<table role="presentation"><tr>'
            '<td style="color: #333333; position: absolute; font-family: Arial, sans-serif;">'
            "text</td></tr></table>"
        )
        rendered = (
            '<table role="presentation"><tr>'
            '<td style="color: #333333; font-family: Arial, sans-serif;">'
            "text</td></tr></table>"
        )
        diff = compute_dom_diff(original, rendered)
        removed_props = [p for props in diff.removed_css_properties.values() for p in props]
        assert "position" in removed_props

    def test_modified_style(self) -> None:
        original = (
            '<table role="presentation"><tr>'
            '<td style="margin: 10px; mso-table-lspace: 0pt;">text</td>'
            "</tr></table>"
        )
        rendered = (
            '<table role="presentation"><tr>'
            '<td style="margin: 0; mso-table-lspace: 0pt;">text</td>'
            "</tr></table>"
        )
        diff = compute_dom_diff(original, rendered)
        assert any("margin" in k for k in diff.modified_styles)

    def test_invalid_html_returns_empty_diff(self) -> None:
        diff = compute_dom_diff("", "")
        assert isinstance(diff, DOMDiff)

    def test_added_elements(self) -> None:
        original = '<table role="presentation"><tr><td>Hello</td></tr></table>'
        rendered = (
            '<table role="presentation"><tr><td>Hello</td></tr>'
            "<tr><td><span>Added by sanitizer</span></td></tr></table>"
        )
        diff = compute_dom_diff(original, rendered)
        assert "span" in diff.added_elements

    def test_removed_attribute(self) -> None:
        original = (
            '<table role="presentation"><tr><td>'
            '<img src="logo.png" alt="Logo" data-slot="header_logo">'
            "</td></tr></table>"
        )
        rendered = (
            '<table role="presentation"><tr><td><img src="logo.png" alt="Logo"></td></tr></table>'
        )
        diff = compute_dom_diff(original, rendered)
        removed = [a for attrs in diff.removed_attributes.values() for a in attrs]
        assert "data-slot" in removed

    def test_stripped_mso_properties(self) -> None:
        original = (
            '<table role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;">'
            "<tr><td>Content</td></tr></table>"
        )
        rendered = '<table role="presentation"><tr><td>Content</td></tr></table>'
        diff = compute_dom_diff(original, rendered)
        removed_props = [p for props in diff.removed_css_properties.values() for p in props]
        assert "mso-table-lspace" in removed_props
        assert "mso-table-rspace" in removed_props
