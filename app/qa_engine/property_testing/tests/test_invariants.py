"""Tests for email invariants."""

from app.qa_engine.property_testing.invariants import (
    ALL_INVARIANTS,
    AltTextPresence,
    ContrastRatio,
    DarkModeReady,
    EncodingValid,
    ImageWidth,
    LinkIntegrity,
    MSOBalance,
    SizeLimit,
    TableNestingDepth,
    ViewportFit,
)

VALID_EMAIL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Test</title></head>
<body style="color:#000000; background-color:#ffffff;">
<table role="presentation" width="600"><tr><td>
<img src="https://example.com/img.png" width="300" alt="Hero image">
<a href="https://example.com">Click here</a>
</td></tr></table></body></html>"""


class TestSizeLimit:
    def test_pass_small_email(self):
        result = SizeLimit().check(VALID_EMAIL)
        assert result.passed

    def test_fail_oversized_email(self):
        html = VALID_EMAIL + "x" * 200_000
        result = SizeLimit().check(html)
        assert not result.passed
        assert "102,400" in result.violations[0]


class TestImageWidth:
    def test_pass_valid_width(self):
        result = ImageWidth().check(VALID_EMAIL)
        assert result.passed

    def test_fail_oversized_image(self):
        html = '<html><body><img src="x.png" width="800" alt="big"></body></html>'
        result = ImageWidth().check(html)
        assert not result.passed

    def test_fail_inline_style_oversized(self):
        html = '<html><body><img src="x.png" alt="big" style="width:700px;"></body></html>'
        result = ImageWidth().check(html)
        assert not result.passed


class TestLinkIntegrity:
    def test_pass_valid_links(self):
        result = LinkIntegrity().check(VALID_EMAIL)
        assert result.passed

    def test_fail_javascript_uri(self):
        html = '<html><body><a href="javascript:alert(1)">click</a></body></html>'
        result = LinkIntegrity().check(html)
        assert not result.passed

    def test_fail_empty_href(self):
        html = '<html><body><a href="">click</a></body></html>'
        result = LinkIntegrity().check(html)
        assert not result.passed


class TestAltTextPresence:
    def test_pass_with_alt(self):
        result = AltTextPresence().check(VALID_EMAIL)
        assert result.passed

    def test_fail_missing_alt(self):
        html = '<html><body><img src="x.png"></body></html>'
        result = AltTextPresence().check(html)
        assert not result.passed

    def test_skip_tracking_pixel(self):
        html = '<html><body><img src="x.png" width="1" height="1"></body></html>'
        result = AltTextPresence().check(html)
        assert result.passed


class TestTableNestingDepth:
    def test_pass_shallow_nesting(self):
        result = TableNestingDepth().check(VALID_EMAIL)
        assert result.passed

    def test_fail_deep_nesting(self):
        html = "<html><body>"
        for _ in range(10):
            html += "<table><tr><td>"
        html += "content"
        for _ in range(10):
            html += "</td></tr></table>"
        html += "</body></html>"
        result = TableNestingDepth().check(html)
        assert not result.passed


class TestEncodingValid:
    def test_pass_valid_utf8(self):
        result = EncodingValid().check(VALID_EMAIL)
        assert result.passed

    def test_fail_null_byte(self):
        html = "<html><body>Hello\x00World</body></html>"
        result = EncodingValid().check(html)
        assert not result.passed


class TestMSOBalance:
    def test_pass_balanced(self):
        html = (
            "<html><body>"
            "<!--[if mso]><table><tr><td><![endif]-->"
            "content"
            "<!--[if mso]></td></tr></table><![endif]-->"
            "</body></html>"
        )
        result = MSOBalance().check(html)
        assert result.passed

    def test_pass_no_mso(self):
        result = MSOBalance().check(VALID_EMAIL)
        assert result.passed

    def test_fail_unbalanced(self):
        html = "<html><body><!--[if mso]><table><tr><td></body></html>"
        result = MSOBalance().check(html)
        assert not result.passed


class TestDarkModeReady:
    def test_pass_no_dark_mode(self):
        result = DarkModeReady().check(VALID_EMAIL)
        assert result.passed

    def test_pass_complete_dark_mode(self):
        html = """<html><head>
        <meta name="color-scheme" content="light dark">
        <style>@media (prefers-color-scheme: dark) { body { background: #1a1a2e; } }</style>
        </head><body></body></html>"""
        result = DarkModeReady().check(html)
        assert result.passed

    def test_fail_incomplete_dark_mode(self):
        html = """<html><head>
        <style>@media (prefers-color-scheme: dark) { body { background: #1a1a2e; } }</style>
        </head><body></body></html>"""
        result = DarkModeReady().check(html)
        assert not result.passed


class TestContrastRatio:
    def test_pass_high_contrast(self):
        html = (
            '<html><body><p style="color:#000000; background-color:#ffffff;">text</p></body></html>'
        )
        result = ContrastRatio().check(html)
        assert result.passed

    def test_fail_low_contrast(self):
        html = (
            '<html><body><p style="color:#777777; background-color:#888888;">text</p></body></html>'
        )
        result = ContrastRatio().check(html)
        assert not result.passed


class TestViewportFit:
    def test_pass_within_600(self):
        result = ViewportFit().check(VALID_EMAIL)
        assert result.passed

    def test_fail_oversized_table(self):
        html = '<html><body><table width="800"><tr><td>content</td></tr></table></body></html>'
        result = ViewportFit().check(html)
        assert not result.passed

    def test_fail_inline_style_oversized(self):
        html = '<html><body><div style="width:700px;">content</div></body></html>'
        result = ViewportFit().check(html)
        assert not result.passed


class TestContrastRatioEdge:
    def test_no_inline_styles_passes(self):
        html = "<html><body><p>No inline styles at all</p></body></html>"
        result = ContrastRatio().check(html)
        assert result.passed


class TestViewportFitEdge:
    def test_no_width_attributes_passes(self):
        html = "<html><body><div>No explicit widths</div><table><tr><td>ok</td></tr></table></body></html>"
        result = ViewportFit().check(html)
        assert result.passed


class TestAltTextEdge:
    def test_empty_alt_fails(self):
        """<img alt=""> should fail for non-tracking images."""
        html = '<html><body><img src="photo.jpg" width="300" height="200" alt=""></body></html>'
        result = AltTextPresence().check(html)
        assert not result.passed


class TestMSOBalanceEdge:
    def test_multiple_balanced_pairs(self):
        html = (
            "<html><body>"
            "<!--[if mso]><table><tr><td><![endif]-->"
            "content1"
            "<!--[if mso]></td></tr></table><![endif]-->"
            "<!--[if mso]><table><tr><td><![endif]-->"
            "content2"
            "<!--[if mso]></td></tr></table><![endif]-->"
            "</body></html>"
        )
        result = MSOBalance().check(html)
        assert result.passed


class TestAllInvariantsRegistered:
    def test_all_10_registered(self):
        assert len(ALL_INVARIANTS) == 10

    def test_names_unique(self):
        names = list(ALL_INVARIANTS.keys())
        assert len(names) == len(set(names))
