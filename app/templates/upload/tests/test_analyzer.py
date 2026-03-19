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
      <tr><td>
        <img src="hero.jpg" width="600" height="300">
        <h1 style="font-family: Arial; font-size: 28px; color: #333333;">Weekly Newsletter</h1>
        <p style="font-family: Arial; font-size: 16px; color: #666666;">Welcome to our weekly roundup of the best content.</p>
        <a href="#" style="background-color: #0066CC; color: #FFFFFF; padding: 12px 24px;">Read More</a>
      </td></tr>
    </table>
  </td></tr>
  <tr><td>
    <table width="600">
      <tr><td style="padding: 20px;">
        <h2 style="font-family: Georgia; font-size: 22px; color: #333333;">Article One</h2>
        <p style="font-family: Arial; font-size: 14px; color: #666666;">Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
      </td></tr>
    </table>
  </td></tr>
  <tr><td>
    <table width="600">
      <tr><td style="padding: 20px;">
        <h2 style="font-family: Georgia; font-size: 22px; color: #333333;">Article Two</h2>
        <p style="font-family: Arial; font-size: 14px; color: #666666;">Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
      </td></tr>
    </table>
  </td></tr>
  <tr><td>
    <table width="600">
      <tr><td style="font-size: 12px; color: #999999;">
        <p>You are receiving this because you subscribed. <a href="#">Unsubscribe</a></p>
        <p>&copy; 2026 Company Inc. All rights reserved.</p>
      </td></tr>
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
  <tr><td>
    <img src="hero-banner.jpg" width="600" height="400">
    <h1 style="font-size: 32px; color: #FF0000;">MEGA SALE - 50% OFF!</h1>
    <p style="font-size: 18px; color: #333333;">Don't miss our biggest sale event of the year.</p>
    <a href="#" class="button" style="background-color: #FF0000; color: #FFFFFF; padding: 16px 32px;">Shop Now</a>
  </td></tr>
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
