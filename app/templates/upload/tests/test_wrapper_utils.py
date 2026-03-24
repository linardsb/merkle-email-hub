"""Tests for wrapper detection and injection utilities."""

from __future__ import annotations

from app.templates.upload.wrapper_utils import detect_centering, inject_centering_wrapper

# ── Fixtures ──

CENTERED_TABLE_HTML = """
<html>
<body>
<table width="600" align="center" cellpadding="0" cellspacing="0" border="0">
  <tr><td>
    <table width="600">
      <tr><td><h1 style="font-size: 24px;">Hello</h1></td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""

CENTERED_DIV_HTML = """
<html>
<body>
<div style="max-width: 600px; margin: 0 auto;">
  <table width="600">
    <tr><td><h1 style="font-size: 24px;">Hello</h1></td></tr>
  </table>
</div>
</body>
</html>
"""

CENTERED_CENTER_TAG_HTML = """
<html>
<body>
<center>
  <table width="600">
    <tr><td><h1 style="font-size: 24px;">Hello</h1></td></tr>
  </table>
</center>
</body>
</html>
"""

MSO_CENTERED_HTML = """
<html>
<body>
<!--[if mso]><table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0"><tr><td><![endif]-->
<div style="max-width: 600px; margin: 0 auto;">
  <table width="600">
    <tr><td><h1 style="font-size: 24px;">Hello</h1></td></tr>
  </table>
</div>
<!--[if mso]></td></tr></table><![endif]-->
</body>
</html>
"""

UNCENTERED_HTML = """
<html>
<body>
<table width="600">
  <tr><td><h1 style="font-size: 24px;">Hello</h1></td></tr>
</table>
<table width="600">
  <tr><td><p style="margin:0 0 10px 0;">Body text content here for testing purposes.</p></td></tr>
</table>
</body>
</html>
"""


class TestDetectCentering:
    def test_centered_table(self) -> None:
        assert detect_centering(CENTERED_TABLE_HTML) is True

    def test_centered_div(self) -> None:
        assert detect_centering(CENTERED_DIV_HTML) is True

    def test_centered_center_tag(self) -> None:
        assert detect_centering(CENTERED_CENTER_TAG_HTML) is True

    def test_mso_centered(self) -> None:
        assert detect_centering(MSO_CENTERED_HTML) is True

    def test_uncentered(self) -> None:
        assert detect_centering(UNCENTERED_HTML) is False


class TestInjectCenteringWrapper:
    def test_injects_wrapper_on_uncentered(self) -> None:
        result = inject_centering_wrapper(UNCENTERED_HTML, width=600)
        assert "max-width: 600px" in result
        assert "margin: 0 auto" in result
        assert "<!--[if mso]>" in result

    def test_no_double_wrap_on_centered(self) -> None:
        result = inject_centering_wrapper(CENTERED_TABLE_HTML, width=600)
        assert result == CENTERED_TABLE_HTML

    def test_custom_width(self) -> None:
        result = inject_centering_wrapper(UNCENTERED_HTML, width=700)
        assert "max-width: 700px" in result
        assert 'width="700"' in result

    def test_preserves_mso_wrapper_verbatim(self) -> None:
        mso = '<!--[if mso]><table role="presentation" width="640" align="center"><tr><td><![endif]-->'
        result = inject_centering_wrapper(UNCENTERED_HTML, width=640, mso_wrapper=mso)
        assert 'width="640"' in result
        assert mso in result

    def test_preserves_body_content(self) -> None:
        result = inject_centering_wrapper(UNCENTERED_HTML, width=600)
        assert "Hello" in result
        assert "Body text content" in result
