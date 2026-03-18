"""Tests for 24B.6 — Per-Agent nh3 Allowlists."""

from __future__ import annotations

import pytest

from app.ai.shared import (
    PROFILES,
    _extract_vml_blocks,
    _restore_vml_blocks,
    sanitize_html_xss,
)


class TestDefaultProfile:
    """Default profile matches current behavior."""

    def test_preserves_email_tags(self) -> None:
        html = '<table><tr><td style="color: red;">Hello</td></tr></table>'
        result = sanitize_html_xss(html)
        assert "<table>" in result
        assert "<td" in result
        assert "color: red" in result

    def test_strips_script_tags(self) -> None:
        html = '<p>Hello</p><script>alert("xss")</script>'
        result = sanitize_html_xss(html)
        assert "<script>" not in result
        assert "alert" not in result


class TestContentProfile:
    """Content profile strips structural tags."""

    def test_strips_table_tags(self) -> None:
        html = '<table><tr><td><p>Hello <strong>world</strong></p></td></tr></table>'
        result = sanitize_html_xss(html, profile="content")
        assert "<table>" not in result
        assert "<p>" in result
        assert "<strong>" in result

    def test_preserves_inline_tags(self) -> None:
        html = '<p>Hello <em>world</em> <a href="https://example.com">link</a></p>'
        result = sanitize_html_xss(html, profile="content")
        assert "<em>" in result
        assert "<a " in result


class TestAccessibilityProfile:
    """Accessibility profile preserves ARIA attributes."""

    def test_preserves_aria_attributes(self) -> None:
        html = '<div role="navigation" aria-live="polite" aria-expanded="true" tabindex="0">Nav</div>'
        result = sanitize_html_xss(html, profile="accessibility")
        assert 'aria-live="polite"' in result
        assert 'aria-expanded="true"' in result
        assert 'tabindex="0"' in result


class TestOutlookProfile:
    """Outlook profile preserves VML blocks."""

    def test_preserves_vml_blocks(self) -> None:
        html = """<html><body>
        <p>Before</p>
        <!--[if mso]>
        <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" style="width:200px;height:40px;">
            <v:textbox>Button</v:textbox>
        </v:roundrect>
        <![endif]-->
        <p>After</p>
        </body></html>"""
        result = sanitize_html_xss(html, profile="outlook_fixer")
        assert "v:roundrect" in result
        assert "v:textbox" in result


class TestCodeReviewerProfile:
    """Code reviewer catches HTML leakage."""

    def test_strips_all_html(self) -> None:
        html = "<p>This should not appear as HTML</p>"
        result = sanitize_html_xss(html, profile="code_reviewer")
        assert "<p>" not in result


class TestInnovationProfile:
    """Innovation profile allows form elements."""

    def test_allows_form_elements(self) -> None:
        html = '<form action="/submit" method="post"><input type="text" name="email"><button type="submit">Go</button></form>'
        result = sanitize_html_xss(html, profile="innovation")
        assert "<form" in result
        assert "<input" in result
        assert "<button" in result


class TestVMLExtractRestore:
    """VML block extract/restore round-trip."""

    def test_round_trip(self) -> None:
        original_block = '<!--[if mso]><v:rect style="width:100px;"><v:textbox>Text</v:textbox></v:rect><![endif]-->'
        html = f"<p>Before</p>{original_block}<p>After</p>"
        stripped, blocks = _extract_vml_blocks(html)
        assert "v:rect" not in stripped
        assert len(blocks) == 1
        restored = _restore_vml_blocks(stripped, blocks)
        assert "v:rect" in restored
        assert restored == html


class TestUnknownProfile:
    """Unknown profile falls back to default."""

    def test_unknown_falls_back(self) -> None:
        html = "<table><tr><td>Hello</td></tr></table>"
        result = sanitize_html_xss(html, profile="nonexistent")
        # Should not crash, should use default
        assert "<table>" in result


class TestAllProfilesPreserveComments:
    """All profiles allow email-safe HTML comments."""

    def test_comments_preserved(self) -> None:
        html = "<!-- Email preview text --><p>Hello</p>"
        for profile_name in PROFILES:
            if profile_name == "code_reviewer":
                continue  # code_reviewer strips everything
            result = sanitize_html_xss(html, profile=profile_name)
            assert "<!-- Email preview text -->" in result, (
                f"Profile {profile_name} stripped comments"
            )
