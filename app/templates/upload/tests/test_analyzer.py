"""Unit tests for TemplateAnalyzer."""

import pytest

from app.templates.upload.analyzer import TemplateAnalyzer

# ── Test HTML fixtures ──

NEWSLETTER_HTML = """
<html>
<body>
<table role="presentation" width="600">
  <tr><td>
    <table width="600">
      <tr><td><img src="logo.png" width="150" height="50"></td></tr>
    </table>
  </td></tr>
  <tr><td>
    <table width="600">
      <tr><td><img src="hero.jpg" width="600" height="300"></td></tr>
      <tr><td><h1 style="font-family: Arial; font-size: 28px; color: #333333;">Weekly Newsletter</h1></td></tr>
      <tr><td><p style="margin:0 0 10px 0; font-family: Arial; font-size: 16px; color: #666666;">Welcome to our weekly roundup of the best content.</p></td></tr>
      <tr><td><a href="#" style="background-color: #0066CC; color: #FFFFFF; padding: 12px 24px;">Read More</a></td></tr>
    </table>
  </td></tr>
  <tr><td>
    <table width="600">
      <tr><td style="padding: 20px;"><h2 style="font-family: Georgia; font-size: 22px; color: #333333;">Article One</h2></td></tr>
      <tr><td style="padding: 20px;"><p style="margin:0; font-family: Arial; font-size: 14px; color: #666666;">Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p></td></tr>
    </table>
  </td></tr>
  <tr><td>
    <table width="600">
      <tr><td style="padding: 20px;"><h2 style="font-family: Georgia; font-size: 22px; color: #333333;">Article Two</h2></td></tr>
      <tr><td style="padding: 20px;"><p style="margin:0; font-family: Arial; font-size: 14px; color: #666666;">Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p></td></tr>
    </table>
  </td></tr>
  <tr><td>
    <table width="600">
      <tr><td style="font-size: 12px; color: #999999;"><p style="margin:0 0 10px 0;">You are receiving this because you subscribed. <a href="#">Unsubscribe</a></p></td></tr>
      <tr><td style="font-size: 12px; color: #999999;"><p style="margin:0;">&copy; 2026 Company Inc. All rights reserved.</p></td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""

PROMOTIONAL_HTML = """
<html>
<body>
<table width="600">
  <tr><td><img src="hero-banner.jpg" width="600" height="400"></td></tr>
  <tr><td><h1 style="font-size: 32px; color: #FF0000;">MEGA SALE - 50% OFF!</h1></td></tr>
  <tr><td><p style="margin:0 0 10px 0; font-size: 18px; color: #333333;">Don't miss our biggest sale event of the year.</p></td></tr>
  <tr><td><a href="#" class="button" style="background-color: #FF0000; color: #FFFFFF; padding: 16px 32px;">Shop Now</a></td></tr>
</table>
</body>
</html>
"""

BRAZE_HTML = """
<html><body>
<p>Hello {{${first_name}}},</p>
<p>{{content_blocks.${welcome_block}}}</p>
{% connected_content https://api.example.com/user %}
</body></html>
"""

MAILCHIMP_HTML = """
<html><body>
<p>Hello *|FNAME|*,</p>
<p>Thanks for joining *|LIST:COMPANY|*</p>
</body></html>
"""

AMPSCRIPT_HTML = """
<html><body>
<p>Hello %%=v(@FirstName)=%%,</p>
<p>Your order %%Order_ID%% has shipped.</p>
</body></html>
"""

MSO_COMPLEX_HTML = """
<html><body>
<!--[if mso]><table><tr><td><![endif]-->
<div style="display: grid;">
  <table><tr><td>
    <table><tr><td>
      <table><tr><td>Deeply nested</td></tr></table>
    </td></tr></table>
  </td></tr></table>
</div>
<!--[if mso]></td></tr></table><![endif]-->
<!--[if gte vml 1]><v:rect><![endif]-->
</body></html>
"""


@pytest.fixture
def analyzer() -> TemplateAnalyzer:
    return TemplateAnalyzer()


class TestSectionDetection:
    def test_newsletter_detects_multiple_sections(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NEWSLETTER_HTML)
        assert len(result.sections) >= 3

    def test_promotional_detects_hero(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(PROMOTIONAL_HTML)
        has_hero = any(s.component_name in ("hero", "content") for s in result.sections)
        assert has_hero

    def test_sections_have_ids(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NEWSLETTER_HTML)
        ids = [s.section_id for s in result.sections]
        assert len(ids) == len(set(ids)), "Section IDs must be unique"


class TestSlotExtraction:
    def test_newsletter_extracts_text_slots(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NEWSLETTER_HTML)
        text_types = {s.slot_type for s in result.slots}
        assert "headline" in text_types or "body" in text_types

    def test_newsletter_extracts_image_slots(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NEWSLETTER_HTML)
        image_slots = [s for s in result.slots if s.slot_type == "image"]
        assert len(image_slots) >= 1

    def test_promotional_extracts_cta(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(PROMOTIONAL_HTML)
        cta_slots = [s for s in result.slots if s.slot_type == "cta"]
        assert len(cta_slots) >= 1

    def test_slot_ids_unique(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NEWSLETTER_HTML)
        ids = [s.slot_id for s in result.slots]
        assert len(ids) == len(set(ids))


class TestTokenExtraction:
    def test_extracts_colors(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NEWSLETTER_HTML)
        assert result.tokens.colors.get("all"), "Should extract at least some colors"

    def test_extracts_fonts(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NEWSLETTER_HTML)
        all_fonts = list(result.tokens.fonts.get("heading", [])) + list(
            result.tokens.fonts.get("body", [])
        )
        assert len(all_fonts) >= 1


class TestESPDetection:
    def test_detects_braze(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(BRAZE_HTML)
        assert result.esp_platform == "braze"

    def test_detects_mailchimp(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(MAILCHIMP_HTML)
        assert result.esp_platform == "mailchimp"

    def test_detects_salesforce(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(AMPSCRIPT_HTML)
        assert result.esp_platform == "salesforce"

    def test_no_esp_in_plain_html(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(PROMOTIONAL_HTML)
        assert result.esp_platform is None


class TestComplexity:
    def test_simple_template_low_score(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(PROMOTIONAL_HTML)
        assert result.complexity.score < 50

    def test_complex_template_higher_score(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(MSO_COMPLEX_HTML)
        assert result.complexity.mso_conditional_count >= 2
        assert result.complexity.has_vml is True

    def test_table_nesting_measured(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(MSO_COMPLEX_HTML)
        assert result.complexity.table_nesting_depth >= 2


class TestLayoutInference:
    def test_newsletter_detected(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NEWSLETTER_HTML)
        assert result.layout_type == "newsletter"

    def test_promotional_detected(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(PROMOTIONAL_HTML)
        assert result.layout_type == "promotional"

    def test_transactional_detected(self, analyzer: TemplateAnalyzer) -> None:
        html = """<html><body>
        <h1>Order Confirmation</h1>
        <table><tr><td>Item</td><td>Price</td></tr>
        <tr><td>Widget</td><td>$9.99</td></tr></table>
        <p>Your order has been confirmed. Shipping details below.</p>
        </body></html>"""
        result = analyzer.analyze(html)
        assert result.layout_type == "transactional"


# ── Wrapper preservation fixtures ──

WRAPPER_WITH_ATTRS_HTML = """
<html>
<body>
<table width="600" align="center" bgcolor="#ffffff" cellpadding="0" cellspacing="0" border="0" role="presentation" style="max-width: 600px;">
  <tr><td style="max-width: 600px; margin: 0 auto;">
    <table width="600">
      <tr><td><img src="logo.png" width="150" height="50"></td></tr>
    </table>
    <table width="600">
      <tr><td><h1 style="font-size: 24px;">Hello World</h1></td></tr>
      <tr><td><p style="margin:0 0 10px 0; font-size: 14px;">Some body text content here for testing.</p></td></tr>
    </table>
    <table width="600">
      <tr><td style="font-size: 12px;">
        <p style="margin:0;">Footer with unsubscribe link. &copy; 2026 Company</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""

NO_WRAPPER_HTML = """
<html>
<body>
<table width="600">
  <tr><td><img src="logo.png" width="150" height="50"></td></tr>
</table>
<table width="600">
  <tr><td>
    <h1 style="font-size: 24px;">Hello World</h1>
  </td></tr>
</table>
</body>
</html>
"""

MSO_WRAPPER_HTML = """
<html>
<body>
<!--[if mso]><table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table width="600" align="center" cellpadding="0" cellspacing="0" border="0">
  <tr><td>
    <table width="600">
      <tr><td><img src="logo.png" width="150" height="50"></td></tr>
    </table>
    <table width="600">
      <tr><td><h1 style="font-size: 24px;">Content heading here</h1></td></tr>
      <tr><td><p style="margin:0 0 10px 0; font-size: 14px;">Some body text content here for testing.</p></td></tr>
    </table>
  </td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</body>
</html>
"""


class TestWrapperPreservation:
    def test_wrapper_attrs_preserved(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(WRAPPER_WITH_ATTRS_HTML)
        assert result.wrapper is not None
        assert result.wrapper.tag == "table"
        assert result.wrapper.width == "600"
        assert result.wrapper.align == "center"
        assert result.wrapper.bgcolor == "#ffffff"
        assert result.wrapper.cellpadding == "0"
        assert result.wrapper.cellspacing == "0"
        assert result.wrapper.border == "0"
        assert result.wrapper.role == "presentation"

    def test_wrapper_inner_td_style_preserved(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(WRAPPER_WITH_ATTRS_HTML)
        assert result.wrapper is not None
        assert result.wrapper.inner_td_style is not None
        assert "max-width" in result.wrapper.inner_td_style

    def test_no_wrapper_when_multiple_top_level_tables(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(NO_WRAPPER_HTML)
        assert result.wrapper is None

    def test_mso_wrapper_captured(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(MSO_WRAPPER_HTML)
        assert result.wrapper is not None
        assert result.wrapper.mso_wrapper is not None
        assert "<!--[if mso]>" in result.wrapper.mso_wrapper
        assert 'width="600"' in result.wrapper.mso_wrapper

    def test_wrapper_style_attr_preserved(self, analyzer: TemplateAnalyzer) -> None:
        result = analyzer.analyze(WRAPPER_WITH_ATTRS_HTML)
        assert result.wrapper is not None
        assert result.wrapper.style is not None
        assert "max-width" in result.wrapper.style

    def test_sections_still_detected_with_wrapper(self, analyzer: TemplateAnalyzer) -> None:
        """Wrapper extraction must not break section detection."""
        result = analyzer.analyze(WRAPPER_WITH_ATTRS_HTML)
        assert len(result.sections) >= 2

    def test_inner_mso_ghost_table_not_captured_as_wrapper_mso(
        self, analyzer: TemplateAnalyzer
    ) -> None:
        """MSO ghost tables inside sections must not be captured as wrapper MSO."""
        html = """
<html>
<body>
<table width="600" align="center" cellpadding="0" cellspacing="0" border="0">
  <tr><td>
    <table width="600">
      <tr><td><img src="logo.png" width="150" height="50"></td></tr>
    </table>
    <table width="600">
      <tr><td>
        <!--[if mso]><table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td width="300" valign="top"><![endif]-->
        <div style="display: inline-block; max-width: 300px;">Column 1</div>
        <!--[if mso]></td><td width="300" valign="top"><![endif]-->
        <div style="display: inline-block; max-width: 300px;">Column 2</div>
        <!--[if mso]></td></tr></table><![endif]-->
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""
        result = analyzer.analyze(html)
        assert result.wrapper is not None
        # No MSO wrapper before the <table> — the MSO is inside a section
        assert result.wrapper.mso_wrapper is None
