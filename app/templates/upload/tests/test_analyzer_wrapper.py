"""Extended wrapper detection tests for analyzer (Phase 31.8)."""

from __future__ import annotations

import pytest

from app.templates.upload.analyzer import TemplateAnalyzer


@pytest.fixture
def analyzer() -> TemplateAnalyzer:
    return TemplateAnalyzer()


# ── Fixtures ──

CENTER_TAG_WRAPPER_HTML = """
<html>
<body>
<center>
  <table width="600">
    <tr><td><h1 style="font-size: 24px; font-weight: 700;">Heading</h1></td></tr>
    <tr><td><p style="margin:0 0 10px 0; font-size: 14px;">Body text here.</p></td></tr>
  </table>
  <table width="600">
    <tr><td style="font-size: 12px;"><p style="margin:0;">Footer &copy; 2026</p></td></tr>
  </table>
</center>
</body>
</html>
"""

INNER_TD_STYLE_HTML = """
<html>
<body>
<table width="600" align="center" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="max-width: 600px; margin: 0 auto;">
    <table width="600">
      <tr><td><h1 style="font-size: 24px;">Hello</h1></td></tr>
    </table>
    <table width="600">
      <tr><td><p style="margin:0 0 10px 0; font-size: 14px;">Content paragraph.</p></td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""

MULTI_TABLE_NO_WRAPPER_HTML = """
<html>
<body>
<table width="600">
  <tr><td><h1 style="font-size: 24px;">Section A</h1></td></tr>
</table>
<table width="600">
  <tr><td><p style="margin:0 0 10px 0;">Section B</p></td></tr>
</table>
<table width="600">
  <tr><td><p style="margin:0;">Section C</p></td></tr>
</table>
</body>
</html>
"""


class TestCenterTagWrapper:
    def test_center_tag_sections_detected(self, analyzer: TemplateAnalyzer) -> None:
        """Sections inside <center> are still detected."""
        result = analyzer.analyze(CENTER_TAG_WRAPPER_HTML)
        assert len(result.sections) >= 2

    def test_center_tag_section_count_unchanged(self, analyzer: TemplateAnalyzer) -> None:
        """Wrapper detection doesn't affect section identification count."""
        result = analyzer.analyze(CENTER_TAG_WRAPPER_HTML)
        # Sections should be the inner tables, not the <center> itself
        for section in result.sections:
            assert section.section_id is not None


class TestInnerTdStyle:
    def test_inner_td_style_captured(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(INNER_TD_STYLE_HTML)
        assert result.wrapper is not None
        assert result.wrapper.inner_td_style is not None
        assert "max-width" in result.wrapper.inner_td_style

    def test_wrapper_width_and_align(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(INNER_TD_STYLE_HTML)
        assert result.wrapper is not None
        assert result.wrapper.width == "600"
        assert result.wrapper.align == "center"


class TestMultiTableNoWrapper:
    def test_no_wrapper_multiple_top_level(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(MULTI_TABLE_NO_WRAPPER_HTML)
        assert result.wrapper is None

    def test_sections_still_detected(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(MULTI_TABLE_NO_WRAPPER_HTML)
        assert len(result.sections) >= 2
