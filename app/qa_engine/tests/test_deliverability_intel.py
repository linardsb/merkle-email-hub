"""Tests for ISP-aware deliverability intelligence (Phase 25.13)."""

from __future__ import annotations

import pytest

from app.qa_engine.checks.deliverability import DeliverabilityCheck, get_detailed_result
from app.qa_engine.deliverability_analyzer import (
    analyze,
    brightness,
    colors_within_brightness,
    parse_color,
)

# --- Analyzer unit tests ---


class TestColorParsing:
    def test_hex_color(self) -> None:
        assert parse_color("#ffffff") == (255, 255, 255)
        assert parse_color("#000") == (0, 0, 0)

    def test_named_color(self) -> None:
        assert parse_color("white") == (255, 255, 255)
        assert parse_color("black") == (0, 0, 0)

    def test_rgb_color(self) -> None:
        assert parse_color("rgb(255, 0, 0)") == (255, 0, 0)
        assert parse_color("rgba(0, 128, 0, 0.5)") == (0, 128, 0)

    def test_invalid_color(self) -> None:
        assert parse_color("not-a-color") is None
        assert parse_color("#gg") is None


class TestBrightness:
    def test_white_is_bright(self) -> None:
        assert brightness(255, 255, 255) > 0.95

    def test_black_is_dark(self) -> None:
        assert brightness(0, 0, 0) < 0.05

    def test_within_threshold(self) -> None:
        # white-on-white should be within 10%
        assert colors_within_brightness((255, 255, 255), (250, 250, 250), 10)
        # black-on-white should NOT be within 10%
        assert not colors_within_brightness((0, 0, 0), (255, 255, 255), 10)


# --- Full analysis tests ---


class TestAnalyzer:
    def test_clean_email_low_risk(self) -> None:
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head>
        <body>
            <p>Hello {{first_name}},</p>
            <p>We wanted to share some exciting news about our product updates.
            Here are the details you need to know about the improvements we have made
            to help you get the most out of your experience. Our team has been working
            hard over the past few months to bring you these changes and we are thrilled
            to finally share them with you today.</p>
            <p>We have improved performance and added new features based on your feedback.
            These updates include faster load times, better search results, and a more
            intuitive user interface that makes it easier to find what you need. We have
            also addressed several issues that were reported by our community members.</p>
            <p>Thank you for your continued support. We truly appreciate your loyalty
            and look forward to hearing your thoughts on these improvements.</p>
            <a href="https://example.com/learn-more" style="background-color:#0066cc;color:#fff;padding:12px 24px">Learn More</a>
            <footer class="footer">
                <p>123 Main Street, Suite 100, City, ST 12345</p>
                <a href="https://example.com/unsubscribe">Unsubscribe</a>
                <!-- List-Unsubscribe: <mailto:unsub@example.com> -->
            </footer>
        </body></html>"""
        result = analyze(html)
        assert result.overall_risk == "low"
        assert result.hidden_content_count == 0
        assert result.auth_readiness_score >= 20

    def test_image_heavy_flags_gmail(self) -> None:
        html = """<!DOCTYPE html><html><head></head><body>
            <img src="https://cdn.example.com/hero.jpg" width="600" height="400">
            <img src="https://cdn.example.com/product1.jpg" width="300" height="200">
            <img src="https://cdn.example.com/product2.jpg" width="300" height="200">
            <img src="https://cdn.example.com/product3.jpg" width="300" height="200">
            <p>Shop</p>
        </body></html>"""
        result = analyze(html)
        gmail = result.isp_risks.get("gmail")
        assert gmail is not None
        assert any("image-to-text ratio" in f.description.lower() for f in gmail.flags)

    def test_hidden_text_white_on_white(self) -> None:
        html = """<!DOCTYPE html><html><body>
            <div style="color: #fefefe; background-color: #ffffff;">
                Hidden promotional text here that spam filters will catch.
            </div>
            <p>Visible content</p>
        </body></html>"""
        result = analyze(html)
        assert result.hidden_content_count > 0

    def test_gmail_promo_tab_triggers(self) -> None:
        html = """<!DOCTYPE html><html><body>
            <p>Use coupon code SAVE50 for 50% off!</p>
            <p>$29.99 → $14.99 — Limited time offer!</p>
            <p>Free shipping on all orders over $50!</p>
            <a href="#">Shop Now</a>
            <a href="#">Buy Now</a>
        </body></html>"""
        result = analyze(html)
        assert result.gmail_promo_tab_score >= 6
        gmail = result.isp_risks.get("gmail")
        assert gmail is not None
        promo_flags = [f for f in gmail.flags if f.category == "promo_tab"]
        assert len(promo_flags) >= 2

    def test_microsoft_smartscreen_patterns(self) -> None:
        html = """<!DOCTYPE html><html><body>
            <p>Please verify your account by clicking below.</p>
            <a href="#">Click here to confirm your identity</a>
        </body></html>"""
        result = analyze(html)
        ms = result.isp_risks.get("microsoft")
        assert ms is not None
        smartscreen_flags = [f for f in ms.flags if f.category == "smartscreen"]
        assert len(smartscreen_flags) >= 1

    def test_yahoo_missing_footer(self) -> None:
        html = """<!DOCTYPE html><html><body>
            <p>Hello, here is some content.</p>
            <a href="https://example.com/unsub">Unsubscribe</a>
        </body></html>"""
        result = analyze(html)
        yahoo = result.isp_risks.get("yahoo")
        assert yahoo is not None
        assert any("footer" in f.description.lower() for f in yahoo.flags)

    def test_cross_domain_images(self) -> None:
        html = """<!DOCTYPE html><html><body>
            <img src="https://cdn1.example.com/a.jpg" alt="A">
            <img src="https://cdn2.other.com/b.jpg" alt="B">
            <img src="https://images.third.com/c.jpg" alt="C">
            <img src="https://static.fourth.com/d.jpg" alt="D">
        </body></html>"""
        result = analyze(html)
        assert any("domain" in sf.lower() for sf in result.structural_flags)

    def test_responsive_design_warning(self) -> None:
        html = """<!DOCTYPE html><html><body>
            <table width="700"><tr><td>Wide content</td></tr></table>
        </body></html>"""
        result = analyze(html)
        assert any(
            "media query" in sf.lower() or "responsive" in sf.lower()
            for sf in result.structural_flags
        )


# --- Integration with DeliverabilityCheck ---


class TestDeliverabilityCheckIntegration:
    @pytest.fixture()
    def check(self) -> DeliverabilityCheck:
        return DeliverabilityCheck()

    @pytest.mark.asyncio
    async def test_clean_email_passes(self, check: DeliverabilityCheck) -> None:
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head>
        <body>
            <div class="preheader" style="display:none;max-height:0">Preview text for inbox</div>
            <p>Hello {{first_name}},</p>
            <p>Thank you for being a valued customer. We have some updates to share
            with you about improvements to our service. Our team has been working hard
            to make your experience better.</p>
            <img src="https://cdn.example.com/logo.png" alt="Company Logo" width="200">
            <p>Here's what's new:</p>
            <ul><li>Feature A</li><li>Feature B</li><li>Feature C</li></ul>
            <a href="https://example.com/details" style="background-color:#0066cc;color:#fff;padding:12px 24px">Learn More</a>
            <footer class="footer">
                <p>123 Main Street, Suite 100, City, ST 12345</p>
                <a href="https://example.com/unsubscribe">Unsubscribe</a>
                <a href="https://example.com/preferences">Manage Preferences</a>
                <!-- List-Unsubscribe: <mailto:unsub@example.com> -->
            </footer>
        </body></html>"""
        result = await check.run(html)
        assert result.passed is True
        assert result.score >= 0.7
        assert "ISP penalty" in (result.details or "")

    @pytest.mark.asyncio
    async def test_spammy_email_fails(self, check: DeliverabilityCheck) -> None:
        html = """<!DOCTYPE html><html><body>
            <div style="color:#ffffff;background-color:#fefefe">Hidden text here for SEO stuffing</div>
            <img src="https://cdn.example.com/big-banner.jpg" width="600">
            <a href="https://bit.ly/deal1">CLICK HERE</a>
            <a href="https://bit.ly/deal2">BUY NOW</a>
            <a href="https://bit.ly/deal3">FREE STUFF</a>
        </body></html>"""
        result = await check.run(html)
        assert result.passed is False
        assert result.severity in ("error", "warning")

    @pytest.mark.asyncio
    async def test_isp_details_in_output(self, check: DeliverabilityCheck) -> None:
        html = """<!DOCTYPE html><html><body>
            <p>Use coupon code SAVE50!</p>
            <p>$29.99 sale price — Shop Now!</p>
            <a href="https://example.com/shop">Shop Now</a>
        </body></html>"""
        result = await check.run(html)
        details = result.details or ""
        assert "Overall risk:" in details


class TestGetDetailedResult:
    def test_returns_isp_analysis(self) -> None:
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head>
        <body><p>Simple test email content with enough words.</p>
        <a href="https://example.com/unsub">Unsubscribe</a>
        <footer class="footer"><p>123 Main St, City, ST 12345</p></footer>
        </body></html>"""
        score, _passed, dimensions, analysis = get_detailed_result(html)
        assert isinstance(score, int)
        assert len(dimensions) == 4
        assert analysis is not None
        assert hasattr(analysis, "isp_risks")
        assert hasattr(analysis, "overall_risk")


# --- Dimension scoring tests (checks/deliverability.py internals) ---


class TestContentQualityScoring:
    """Test _score_content_quality dimension."""

    def test_high_image_ratio_penalized(self) -> None:
        """Image-heavy email (>60% image area) -> content quality deduction."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td><img src="a.jpg" width="600" height="400" alt=""></td></tr>
          <tr><td><img src="b.jpg" width="600" height="300" alt=""></td></tr>
          <tr><td><img src="c.jpg" width="600" height="300" alt=""></td></tr>
          <tr><td>Short</td></tr>
        </table>
        </body></html>"""
        _score, _, dims, _ = get_detailed_result(html)
        content_dim = next(d for d in dims if "content" in d.name.lower())
        assert content_dim.score < 25  # Penalty for image-dominated

    def test_url_shorteners_penalized(self) -> None:
        """bit.ly/t.co links -> content quality deduction."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td style="font-family:Arial,sans-serif;font-size:14px;color:#333333;">
            Check out our amazing deals on products today and make sure to visit
            our store for the latest updates on everything new and exciting. We have
            been working hard to bring you these new features and improvements.
          </td></tr>
          <tr><td>
            <a href="https://bit.ly/xyz">Click here</a>
            <a href="https://t.co/abc">Learn more</a>
          </td></tr>
        </table>
        </body></html>"""
        _score, _, dims, _ = get_detailed_result(html)
        content_dim = next(d for d in dims if "content" in d.name.lower())
        assert content_dim.score < 25

    def test_balanced_content_scores_well(self) -> None:
        """Good text-to-image ratio -> high content quality score."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td style="font-family:Arial,sans-serif;font-size:14px;color:#333333;">
            We are excited to share our latest product updates with you today.
            Our team has been working hard to improve the user experience and we
            believe these changes will make a real difference in your workflow.
            Here are the key improvements we have made this quarter to bring you
            a better product experience overall.
          </td></tr>
          <tr><td><img src="https://cdn.example.com/logo.png" alt="Logo" width="200"></td></tr>
          <tr><td style="font-family:Arial,sans-serif;font-size:14px;">
            Here are the key improvements we have made this quarter.
          </td></tr>
          <tr><td><a href="https://example.com/details">Learn More</a></td></tr>
        </table>
        </body></html>"""
        _score, _, dims, _ = get_detailed_result(html)
        content_dim = next(d for d in dims if "content" in d.name.lower())
        assert content_dim.score >= 20


class TestHtmlHygieneScoring:
    """Test _score_html_hygiene dimension."""

    def test_missing_doctype_penalized(self) -> None:
        """No DOCTYPE -> hygiene deduction."""
        html = """<html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td>No doctype email with enough content to analyze properly.</td></tr>
        </table>
        </body></html>"""
        _, _, dims, _ = get_detailed_result(html)
        hygiene_dim = next(d for d in dims if "hygiene" in d.name.lower())
        assert hygiene_dim.score < 25

    def test_missing_charset_penalized(self) -> None:
        """No charset meta -> hygiene deduction."""
        html = """<!DOCTYPE html><html><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td>No charset email with content.</td></tr>
        </table>
        </body></html>"""
        _, _, dims, _ = get_detailed_result(html)
        hygiene_dim = next(d for d in dims if "hygiene" in d.name.lower())
        assert hygiene_dim.score < 25

    def test_hidden_text_penalized(self) -> None:
        """Hidden text via color match -> hygiene deduction."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td style="color: #fefefe; background-color: #ffffff;">
            Hidden promotional spam text keywords that should not be visible
          </td></tr>
          <tr><td>Visible content here with enough words.</td></tr>
        </table>
        </body></html>"""
        _, _, dims, _ = get_detailed_result(html)
        hygiene_dim = next(d for d in dims if "hygiene" in d.name.lower())
        assert hygiene_dim.score < 25


class TestAuthReadinessScoring:
    """Test _score_auth_readiness dimension."""

    def test_full_auth_readiness(self) -> None:
        """Unsubscribe link + address + List-Unsubscribe -> high score."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td style="font-family:Arial,sans-serif;font-size:14px;">
            Content here with enough words for the analysis to process properly.
          </td></tr>
        </table>
        <table width="600" cellpadding="0" cellspacing="0" class="footer" role="presentation">
          <tr><td style="font-size:12px;color:#999999;">
            123 Main Street, Suite 100, City, ST 12345<br>
            <a href="https://example.com/unsubscribe">Unsubscribe</a>
            <!-- List-Unsubscribe: <mailto:unsub@example.com> -->
          </td></tr>
        </table>
        </body></html>"""
        _, _, dims, _ = get_detailed_result(html)
        auth_dim = next(d for d in dims if "auth" in d.name.lower())
        assert auth_dim.score >= 20

    def test_missing_unsubscribe(self) -> None:
        """No unsubscribe link -> auth readiness deduction."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td>Content without unsubscribe link for testing purposes.</td></tr>
        </table>
        <table width="600" cellpadding="0" cellspacing="0" class="footer" role="presentation">
          <tr><td style="font-size:12px;">123 Main St, City, ST 12345</td></tr>
        </table>
        </body></html>"""
        _, _, dims, _ = get_detailed_result(html)
        auth_dim = next(d for d in dims if "auth" in d.name.lower())
        assert auth_dim.score < 25


class TestEngagementSignals:
    """Test _score_engagement_signals dimension."""

    def test_preview_text_boosts_score(self) -> None:
        """Preheader/preview text -> engagement signal bonus."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td class="preheader" style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;">
            Preview text for inbox display that is long enough to be detected
          </td></tr>
          <tr><td style="font-family:Arial,sans-serif;font-size:14px;">
            Main content with enough words for engagement scoring to work properly.
            This paragraph needs to be long enough to avoid the short content penalty.
          </td></tr>
          <tr><td>
            <a href="https://example.com/cta" style="background:#0066cc;color:#fff;padding:12px 24px;">Shop Now</a>
          </td></tr>
        </table>
        </body></html>"""
        _, _, dims, _ = get_detailed_result(html)
        eng_dim = next(d for d in dims if "engagement" in d.name.lower())
        assert eng_dim.score >= 15

    def test_personalization_tokens_boost(self) -> None:
        """{{first_name}} merge tag -> engagement bonus."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td style="font-family:Arial,sans-serif;font-size:14px;">
            Hello {{first_name}}, we have exciting news for you today.
            We wanted to share these important updates with you. As a valued
            customer, we believe you will find these changes helpful.
          </td></tr>
          <tr><td>
            <a href="https://example.com" style="background:#0066cc;color:#fff;padding:10px 20px;">Learn More</a>
          </td></tr>
        </table>
        </body></html>"""
        _, _, dims, _ = get_detailed_result(html)
        eng_dim = next(d for d in dims if "engagement" in d.name.lower())
        assert eng_dim.score >= 10

    def test_short_content_penalized(self) -> None:
        """Very short content -> engagement deduction."""
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td>Hi.</td></tr>
        </table>
        </body></html>"""
        _, _, dims, _ = get_detailed_result(html)
        eng_dim = next(d for d in dims if "engagement" in d.name.lower())
        assert eng_dim.score < 20


class TestISPSpecificAnalysis:
    """Isolated ISP-specific analyzer tests."""

    def test_gmail_promo_tab_coupon_trigger(self) -> None:
        """Coupon code pattern triggers Gmail promo tab flag."""
        html = """<!DOCTYPE html><html><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td style="font-family:Arial,sans-serif;font-size:14px;">
            Use code SUMMER2026 for 25% off your order!
            Shop now and save with this exclusive coupon deal!
          </td></tr>
        </table>
        </body></html>"""
        result = analyze(html)
        assert result.gmail_promo_tab_score >= 1

    def test_microsoft_link_count_threshold(self) -> None:
        """15+ links trigger Microsoft SmartScreen flag."""
        link_rows = "\n".join(
            f'<tr><td><a href="https://example.com/link{i}">Link {i}</a></td></tr>'
            for i in range(16)
        )
        html = f"""<!DOCTYPE html><html><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td>Content</td></tr>
          {link_rows}
        </table>
        </body></html>"""
        result = analyze(html)
        ms = result.isp_risks.get("microsoft")
        assert ms is not None
        assert any("link" in f.description.lower() for f in ms.flags)

    def test_yahoo_address_detection(self) -> None:
        """Physical address in footer satisfies Yahoo requirement."""
        html = """<!DOCTYPE html><html><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td>Content here.</td></tr>
        </table>
        <table width="600" cellpadding="0" cellspacing="0" class="footer" role="presentation">
          <tr><td style="font-size:12px;color:#999999;">
            123 Main Street, Suite 500, New York, NY 10001<br>
            <a href="https://example.com/unsub">Unsubscribe</a>
          </td></tr>
        </table>
        </body></html>"""
        result = analyze(html)
        yahoo = result.isp_risks.get("yahoo")
        assert yahoo is not None, "Yahoo ISP profile should be present"
        address_flags = [f for f in yahoo.flags if "address" in f.description.lower()]
        assert len(address_flags) == 0  # No address violation

    def test_tracking_params_flagged(self) -> None:
        """URLs with >8 query params -> structural flag."""
        params = "&".join(f"p{i}=v{i}" for i in range(10))
        html = f"""<!DOCTYPE html><html><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td><a href="https://example.com/track?{params}">Click</a></td></tr>
        </table>
        </body></html>"""
        result = analyze(html)
        assert any(
            "param" in sf.lower() or "tracking" in sf.lower() for sf in result.structural_flags
        )

    def test_yahoo_missing_footer_flagged(self) -> None:
        """No footer element -> Yahoo reputation flag."""
        html = """<!DOCTYPE html><html><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td>Content with no footer element at all.</td></tr>
        </table>
        </body></html>"""
        result = analyze(html)
        yahoo = result.isp_risks.get("yahoo")
        assert yahoo is not None
        assert any("footer" in f.description.lower() for f in yahoo.flags)

    def test_hidden_content_white_on_white(self) -> None:
        """White-on-white text detected as hidden."""
        html = """<!DOCTYPE html><html><body>
        <table width="600" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td style="color: #fefefe; background-color: #ffffff;">
            Hidden text that should be detected as suspicious content by the analyzer
          </td></tr>
          <tr><td>Visible content</td></tr>
        </table>
        </body></html>"""
        result = analyze(html)
        assert result.hidden_content_count > 0
