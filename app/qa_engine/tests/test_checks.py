# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
"""Unit tests for all 10 QA check implementations."""

from app.qa_engine.checks.accessibility import AccessibilityCheck
from app.qa_engine.checks.brand_compliance import BrandComplianceCheck
from app.qa_engine.checks.css_support import CssSupportCheck
from app.qa_engine.checks.dark_mode import DarkModeCheck
from app.qa_engine.checks.fallback import FallbackCheck
from app.qa_engine.checks.file_size import FileSizeCheck
from app.qa_engine.checks.html_validation import HtmlValidationCheck
from app.qa_engine.checks.image_optimization import ImageOptimizationCheck
from app.qa_engine.checks.link_validation import LinkValidationCheck
from app.qa_engine.checks.spam_score import SpamScoreCheck

# ── 1. HTML Validation ──


class TestHtmlValidation:
    check = HtmlValidationCheck()

    async def test_valid_html_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0
        assert result.check_name == "html_validation"

    async def test_missing_doctype_fails(self):
        html = "<html><body>Hello</body></html>"
        result = await self.check.run(html)
        assert result.passed is False
        assert "DOCTYPE" in (result.details or "")

    async def test_missing_html_tag_fails(self):
        html = "<!DOCTYPE html><body>Hello</body>"
        result = await self.check.run(html)
        assert result.passed is False
        assert result.score < 1.0

    async def test_missing_closing_html_fails(self):
        html = "<!DOCTYPE html><html><body>Hello</body>"
        result = await self.check.run(html)
        assert result.passed is False
        assert "closing" in (result.details or "").lower()


# ── 2. CSS Support ──


class TestCssSupport:
    check = CssSupportCheck()

    async def test_no_unsupported_css_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_position_fixed_flagged(self):
        html = "<!DOCTYPE html><html><style>div { position: fixed; }</style></html>"
        result = await self.check.run(html)
        assert result.passed is False
        assert "position" in (result.details or "")

    async def test_display_grid_flagged(self):
        html = "<!DOCTYPE html><html><style>.grid { display: grid; }</style></html>"
        result = await self.check.run(html)
        assert result.passed is False
        assert "display" in (result.details or "")

    async def test_display_flex_flagged(self):
        html = "<!DOCTYPE html><html><style>.flex { display: flex; }</style></html>"
        result = await self.check.run(html)
        assert result.passed is False
        assert "display" in (result.details or "")


# ── 3. File Size ──


class TestFileSize:
    check = FileSizeCheck()

    async def test_small_html_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_over_102kb_fails(self):
        html = "x" * (103 * 1024)  # 103KB
        result = await self.check.run(html)
        assert result.passed is False
        assert result.severity == "error"
        assert "102KB" in (result.details or "")

    async def test_exactly_102kb_passes(self):
        html = "x" * (102 * 1024)
        result = await self.check.run(html)
        assert result.passed is True


# ── 4. Link Validation ──


class TestLinkValidation:
    check = LinkValidationCheck()

    async def test_https_links_pass(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_http_links_flagged(self):
        html = '<a href="http://example.com">Click</a>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "Non-HTTPS" in (result.details or "")

    async def test_mailto_allowed(self):
        html = '<a href="mailto:test@example.com">Email</a>'
        result = await self.check.run(html)
        assert result.passed is True

    async def test_tel_allowed(self):
        html = '<a href="tel:+1234567890">Call</a>'
        result = await self.check.run(html)
        assert result.passed is True

    async def test_liquid_templates_allowed(self):
        html = '<a href="{{ url }}">Link</a>'
        result = await self.check.run(html)
        assert result.passed is True

    async def test_jinja_templates_allowed(self):
        html = '<a href="{% if url %}{{ url }}{% endif %}">Link</a>'
        result = await self.check.run(html)
        assert result.passed is True

    async def test_localhost_http_allowed(self):
        html = '<a href="http://localhost:3000/test">Dev link</a>'
        result = await self.check.run(html)
        assert result.passed is True


# ── 5. Spam Score ──


class TestSpamScore:
    check = SpamScoreCheck()

    async def test_clean_content_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True

    async def test_spam_triggers_flagged(self):
        html = "<html><body><p>Buy now! Free offer! Click here!</p></body></html>"
        result = await self.check.run(html)
        assert result.passed is False or result.score < 1.0
        assert "buy now" in (result.details or "").lower()

    async def test_few_triggers_still_passes(self):
        """Score threshold is 0.5 — up to 3 triggers should still pass."""
        html = "<html><body><p>This is free content with a guarantee.</p></body></html>"
        result = await self.check.run(html)
        # 2 triggers * 0.15 = 0.30 deduction, score = 0.70, still passes
        assert result.passed is True
        assert result.score >= 0.5


# ── 6. Dark Mode ──


class TestDarkMode:
    check = DarkModeCheck()

    async def test_full_dark_mode_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_missing_prefers_color_scheme_degrades(self):
        html = """<html><meta name="color-scheme" content="light dark">
        <style>[data-ogsc] { background: #000; }</style></html>"""
        result = await self.check.run(html)
        assert result.passed is False
        assert "prefers-color-scheme" in (result.details or "")

    async def test_missing_outlook_overrides_degrades(self):
        html = """<html><meta name="color-scheme" content="light dark">
        <style>@media (prefers-color-scheme: dark) { }</style></html>"""
        result = await self.check.run(html)
        assert result.passed is False
        assert "Outlook" in (result.details or "")

    async def test_all_missing_scores_low(self, sample_html_minimal):
        result = await self.check.run(sample_html_minimal)
        assert result.passed is False
        assert result.score < 0.1


# ── 7. Accessibility ──


class TestAccessibility:
    check = AccessibilityCheck()

    async def test_accessible_html_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_missing_lang_degrades(self):
        html = '<!DOCTYPE html><html><body><table role="presentation"></table></body></html>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "lang" in (result.details or "")

    async def test_missing_alt_degrades(self):
        html = '<!DOCTYPE html><html lang="en"><body><img src="test.png"><table role="presentation"></table></body></html>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "alt" in (result.details or "").lower()

    async def test_missing_role_degrades(self):
        html = '<!DOCTYPE html><html lang="en"><body><table></table></body></html>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "role" in (result.details or "").lower()


# ── 8. Fallback ──


class TestFallback:
    check = FallbackCheck()

    async def test_mso_conditionals_present_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_missing_mso_degrades(self):
        html = '<html xmlns:v="urn:schemas-microsoft-com:vml"><body>Hello</body></html>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "MSO" in (result.details or "")

    async def test_missing_vml_degrades(self):
        html = "<html><body><!--[if mso]>test<![endif]--></body></html>"
        result = await self.check.run(html)
        assert result.passed is False
        assert "VML" in (result.details or "")

    async def test_all_missing_scores_low(self, sample_html_minimal):
        result = await self.check.run(sample_html_minimal)
        assert result.passed is False
        assert result.score <= 0.2


# ── 9. Image Optimization ──


class TestImageOptimization:
    check = ImageOptimizationCheck()

    async def test_images_with_dimensions_pass(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_missing_dimensions_degrades(self):
        html = '<html><body><img src="https://example.com/img.png" alt="test"></body></html>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "dimensions" in (result.details or "").lower()

    async def test_bmp_format_flagged(self):
        html = '<html><body><img src="https://example.com/logo.bmp" alt="logo" width="200" height="100"></body></html>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "BMP" in (result.details or "")

    async def test_no_images_passes(self):
        html = "<html><body><p>No images here</p></body></html>"
        result = await self.check.run(html)
        assert result.passed is True


# ── 10. Brand Compliance ──


class TestBrandCompliance:
    check = BrandComplianceCheck()

    async def test_always_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0
        assert result.check_name == "brand_compliance"

    async def test_passes_even_with_minimal_html(self, sample_html_minimal):
        result = await self.check.run(sample_html_minimal)
        assert result.passed is True
        assert result.score == 1.0
