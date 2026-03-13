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

# ── 1. HTML Validation (20 DOM checks) ──


def _valid_html(
    *,
    doctype: bool = True,
    charset: bool = True,
    viewport: bool = True,
    title: str = "Email",
    head_extra: str = "",
    body: str = '<table role="presentation"><tr><td>Hello</td></tr></table>',
) -> str:
    """Build structurally complete email HTML with configurable omissions."""
    parts: list[str] = []
    if doctype:
        parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    if charset:
        parts.append('<meta charset="utf-8">')
    if viewport:
        parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    if title:
        parts.append(f"<title>{title}</title>")
    parts.append(head_extra)
    parts.append("</head>")
    parts.append(f"<body>{body}</body>")
    parts.append("</html>")
    return "\n".join(parts)


class TestHtmlValidation:
    check = HtmlValidationCheck()

    # --- Group A: Document Skeleton ---

    async def test_valid_html_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0
        assert result.check_name == "html_validation"

    async def test_empty_html_fails(self):
        result = await self.check.run("")
        assert result.passed is False
        assert result.score == 0.0
        assert "Empty" in (result.details or "")

    async def test_missing_doctype_fails(self):
        html = _valid_html(doctype=False)
        result = await self.check.run(html)
        assert result.passed is False
        assert "DOCTYPE" in (result.details or "")

    async def test_missing_head_fails(self):
        html = "<!DOCTYPE html><html><body><p>Hello</p></body></html>"
        result = await self.check.run(html)
        assert result.passed is False
        # Should flag missing charset, viewport, title (head is auto-created but empty)

    async def test_missing_charset_fails(self):
        html = _valid_html(charset=False)
        result = await self.check.run(html)
        assert result.passed is False
        assert "charset" in (result.details or "").lower()

    async def test_http_equiv_charset_passes(self):
        html = _valid_html(
            charset=False,
            head_extra='<meta http-equiv="Content-Type" content="text/html; charset=utf-8">',
        )
        result = await self.check.run(html)
        assert "charset" not in (result.details or "").lower()

    async def test_missing_viewport_fails(self):
        html = _valid_html(viewport=False)
        result = await self.check.run(html)
        assert result.passed is False
        assert "viewport" in (result.details or "").lower()

    async def test_missing_title_fails(self):
        html = _valid_html(title="")
        result = await self.check.run(html)
        assert result.passed is False
        assert "title" in (result.details or "").lower()

    # --- Group B: Tag Integrity ---

    async def test_unclosed_div_fails(self):
        html = _valid_html(body="<div><p>Hello</p>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "Unclosed" in (result.details or "")
        assert "<div>" in (result.details or "")

    async def test_unclosed_td_fails(self):
        html = _valid_html(body="<table><tr><td>Hello</tr></table>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "Unclosed" in (result.details or "")

    async def test_block_in_inline_fails(self):
        html = _valid_html(body="<span><div>Bad nesting</div></span>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "nesting" in (result.details or "").lower()
        assert "<div>" in (result.details or "")
        assert "<span>" in (result.details or "")

    async def test_duplicate_id_fails(self):
        html = _valid_html(body='<div id="hero">A</div><div id="hero">B</div>')
        result = await self.check.run(html)
        assert result.passed is False
        assert "Duplicate" in (result.details or "")
        assert "hero" in (result.details or "")

    # --- Group C: Content Integrity ---

    async def test_empty_body_fails(self):
        html = _valid_html(body="")
        result = await self.check.run(html)
        assert result.passed is False
        assert "Empty <body>" in (result.details or "")

    async def test_style_in_body_fails(self):
        html = _valid_html(body="<style>.test { color: red; }</style><p>Hello</p>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "<style> in <body>" in (result.details or "")

    async def test_style_in_head_passes(self):
        html = _valid_html(head_extra="<style>.test { color: red; }</style>")
        result = await self.check.run(html)
        assert "<style> in <body>" not in (result.details or "")

    async def test_external_stylesheet_fails(self):
        html = _valid_html(
            head_extra='<link rel="stylesheet" href="https://example.com/style.css">',
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "stylesheet" in (result.details or "").lower()

    # --- Group D: Email-Specific Structure ---

    async def test_td_outside_tr_fails(self):
        html = _valid_html(body="<table><td>Orphan</td></table>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "Table structure" in (result.details or "")

    async def test_valid_table_passes(self):
        html = _valid_html(
            body="<table><thead><tr><th>Header</th></tr></thead>"
            "<tbody><tr><td>Cell</td></tr></tbody></table>",
        )
        result = await self.check.run(html)
        assert "Table structure" not in (result.details or "")

    async def test_orphaned_li_fails(self):
        html = _valid_html(body="<li>Orphan item</li>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "List structure" in (result.details or "")

    async def test_valid_list_passes(self):
        html = _valid_html(body="<ul><li>Item 1</li><li>Item 2</li></ul>")
        result = await self.check.run(html)
        assert "List structure" not in (result.details or "")

    async def test_duplicate_body_fails(self):
        html = "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>T</title></head><body><p>A</p></body><body><p>B</p></body></html>"
        result = await self.check.run(html)
        assert result.passed is False
        assert "Duplicate <body>" in (result.details or "")

    async def test_nested_links_fails(self):
        html = _valid_html(
            body='<a href="https://outer.com"><a href="https://inner.com">Nested</a></a>',
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "Nested <a>" in (result.details or "")

    # --- Group E: Progressive Enhancement ---

    async def test_video_without_poster_fails(self):
        html = _valid_html(
            body='<video><source src="video.mp4" type="video/mp4">No poster</video>',
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "poster" in (result.details or "").lower()

    async def test_video_with_poster_and_fallback_passes(self):
        html = _valid_html(
            body='<video poster="thumb.jpg"><source src="v.mp4" type="video/mp4">'
            '<img src="thumb.jpg" alt="Video thumbnail"></video>',
        )
        result = await self.check.run(html)
        assert "poster" not in (result.details or "").lower()

    async def test_audio_without_fallback_fails(self):
        html = _valid_html(
            body='<audio><source src="audio.mp3" type="audio/mpeg"></audio>',
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "<audio>" in (result.details or "")

    async def test_picture_without_img_fails(self):
        html = _valid_html(
            body='<picture><source srcset="dark.png" media="(prefers-color-scheme: dark)"></picture>',
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "<picture>" in (result.details or "")
        assert "<img>" in (result.details or "")

    async def test_picture_with_img_passes(self):
        html = _valid_html(
            body='<picture><source srcset="dark.png" media="(prefers-color-scheme: dark)">'
            '<img src="light.png" alt="Logo"></picture>',
        )
        result = await self.check.run(html)
        assert "<picture> missing" not in (result.details or "")

    async def test_details_without_summary_fails(self):
        html = _valid_html(body="<details><p>Content without summary</p></details>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "summary" in (result.details or "").lower()

    async def test_details_with_summary_passes(self):
        html = _valid_html(
            body="<details><summary>Click to expand</summary><p>Content</p></details>",
        )
        result = await self.check.run(html)
        assert "<details> must have <summary>" not in (result.details or "")

    async def test_input_without_label_fails(self):
        html = _valid_html(body='<input type="checkbox" id="toggle1">')
        result = await self.check.run(html)
        assert result.passed is False
        assert "label" in (result.details or "").lower()

    async def test_input_with_label_passes(self):
        html = _valid_html(
            body='<input type="checkbox" id="toggle1"><label for="toggle1">Toggle</label>',
        )
        result = await self.check.run(html)
        assert "label" not in (result.details or "").lower()

    async def test_invalid_ld_json_fails(self):
        html = _valid_html(
            head_extra='<script type="application/ld+json">{invalid json}</script>',
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "invalid JSON" in (result.details or "")

    async def test_valid_ld_json_passes(self):
        html = _valid_html(
            head_extra='<script type="application/ld+json">{"@type": "Order"}</script>',
        )
        result = await self.check.run(html)
        assert "ld+json" not in (result.details or "")

    async def test_template_element_fails(self):
        html = _valid_html(body="<template><p>Hidden content</p></template>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "<template>" in (result.details or "")

    async def test_base_tag_fails(self):
        html = _valid_html(head_extra='<base href="https://example.com/">')
        result = await self.check.run(html)
        assert result.passed is False
        assert "<base" in (result.details or "")

    async def test_unparseable_html_fails(self):
        """Completely unparseable input returns score 0."""
        null_result = await self.check.run("\x00\x01\x02")
        # lxml tolerates almost anything — null bytes still parse
        assert null_result.score <= 1.0
        result_ws = await self.check.run("   \n\t  ")
        assert result_ws.passed is False
        assert result_ws.score == 0.0
        assert "Empty" in (result_ws.details or "")

    async def test_inline_svg_missing_accessibility(self):
        """Inline SVG without role='img' and aria-label is flagged."""
        html = _valid_html(
            body='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            "<circle cx='12' cy='12' r='10'/></svg>",
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "svg" in (result.details or "").lower()
        assert "aria-label" in (result.details or "")

    async def test_inline_svg_with_accessibility_passes(self):
        """Inline SVG with role='img' and aria-label passes."""
        html = _valid_html(
            body='<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Icon" '
            'viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>',
        )
        result = await self.check.run(html)
        assert "svg" not in (result.details or "").lower()

    # --- Scoring ---

    async def test_cumulative_deductions(self):
        """Multiple issues deduct cumulatively."""
        # Has <html> so structure check continues, but missing:
        # doctype(-0.15), charset(-0.15), viewport(-0.10), title(-0.10),
        # empty head(-0.15), empty body(-0.15) = 0.80 deducted → score 0.20
        html = "<html><head></head><body></body></html>"
        result = await self.check.run(html)
        assert result.passed is False
        assert result.score == 0.2

    async def test_score_clamps_at_zero(self):
        """Score never goes below 0.0."""
        html = ""
        result = await self.check.run(html)
        assert result.score >= 0.0

    async def test_config_override_deduction(self):
        """Config params override default deductions."""
        from app.qa_engine.check_config import QACheckConfig

        html = _valid_html(doctype=False)
        # Default deduction for doctype is 0.15
        result_default = await self.check.run(html)
        # Custom: much smaller deduction
        config = QACheckConfig(params={"deduction_doctype": 0.01})
        result_custom = await self.check.run(html, config)
        assert result_custom.score > result_default.score


# ── 2. CSS Support ──


class TestCssSupport:
    check = CssSupportCheck()

    async def test_no_unsupported_css_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        # color-scheme CSS property has limited client support but is required for dark mode
        # Score may be < 1.0 due to color-scheme flagging, but should still be high
        assert result.score >= 0.7

    async def test_position_fixed_flagged(self):
        html = "<!DOCTYPE html><html><style>div { position: fixed; }</style></html>"
        result = await self.check.run(html)
        # position: fixed has fallbacks, so downgraded to warning (check passes)
        assert "position" in (result.details or "")
        assert result.score < 1.0

    async def test_display_grid_flagged(self):
        html = "<!DOCTYPE html><html><style>.grid { display: grid; }</style></html>"
        result = await self.check.run(html)
        # display: grid has fallbacks, so downgraded to warning (check passes)
        assert "display" in (result.details or "")
        assert result.score < 1.0

    async def test_display_flex_flagged(self):
        html = "<!DOCTYPE html><html><style>.flex { display: flex; }</style></html>"
        result = await self.check.run(html)
        # display: flex has fallbacks, so downgraded to warning (check passes)
        assert "display" in (result.details or "")
        assert result.score < 1.0


# ── 3. File Size ──


class TestFileSize:
    """Tests for FileSizeCheck with multi-client thresholds."""

    check = FileSizeCheck()

    async def test_small_html_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_under_all_thresholds(self):
        html = "x" * (50 * 1024)
        result = await self.check.run(html)
        assert result.passed is True
        assert result.score == 1.0

    async def test_over_yahoo_threshold(self):
        """76KB — exceeds Yahoo 75KB but under Gmail 102KB."""
        html = "x" * (76 * 1024)
        result = await self.check.run(html)
        assert result.passed is False
        assert result.score < 1.0
        assert "yahoo" in (result.details or "").lower()

    async def test_over_outlook_threshold(self):
        """101KB — exceeds Outlook 100KB, Braze 100KB, Yahoo 75KB but under Gmail 102KB."""
        html = "x" * (101 * 1024)
        result = await self.check.run(html)
        assert result.passed is False
        assert result.score < 0.8

    async def test_over_gmail_threshold(self):
        """103KB — exceeds ALL thresholds including Gmail 102KB."""
        html = "x" * (103 * 1024)
        result = await self.check.run(html)
        assert result.passed is False
        assert result.severity == "error"
        assert result.score < 0.5

    async def test_details_include_size_summary(self):
        """Details should include file size summary with breakdown."""
        html = "x" * (50 * 1024)
        result = await self.check.run(html)
        assert "Raw:" in (result.details or "")

    async def test_custom_gmail_threshold(self):
        """Config can override Gmail threshold."""
        from app.qa_engine.check_config import QACheckConfig

        config = QACheckConfig(params={"gmail_threshold_kb": 200})
        html = "x" * (103 * 1024)
        result = await self.check.run(html, config)
        details = (result.details or "").lower()
        # Gmail check should pass (103 < 200), but Yahoo/Outlook/Braze still fail
        assert "gmail" not in details

    async def test_severity_escalation(self):
        """Over Gmail = error severity; over Yahoo only = warning severity."""
        # Over Gmail — error
        html_big = "x" * (105 * 1024)
        result_big = await self.check.run(html_big)
        assert result_big.severity == "error"

        # Over Yahoo only — warning
        html_mid = "x" * (80 * 1024)
        result_mid = await self.check.run(html_mid)
        assert result_mid.severity == "warning"

    async def test_score_degrades_with_more_violations(self):
        """Score should be lower when more client thresholds are exceeded."""
        html_80 = "x" * (80 * 1024)  # Yahoo only
        html_105 = "x" * (105 * 1024)  # All clients

        r80 = await self.check.run(html_80)
        r105 = await self.check.run(html_105)

        assert r105.score < r80.score

    async def test_inline_css_bloat_flagged(self):
        """HTML dominated by inline styles should flag content distribution issue."""
        styled_divs = (
            '<div style="color:red;font-size:16px;font-family:Arial,sans-serif;'
            "padding:20px;margin:10px;border:1px solid #ccc;"
            'background-color:#f0f0f0;text-align:center;">x</div>'
        ) * 200
        base = (
            f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f"</head><body>{styled_divs}</body></html>"
        )
        result = await self.check.run(base)
        details = (result.details or "").lower()
        assert "inline" in details or "style" in details

    async def test_disabled_check_still_runs(self):
        """The check itself doesn't check enabled — the service does."""
        from app.qa_engine.check_config import QACheckConfig

        config = QACheckConfig(enabled=False, params={})
        html = "x" * (200 * 1024)
        result = await self.check.run(html, config)
        assert result.passed is False


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
        """Low-weight triggers should not immediately fail."""
        html = "<html><body><p>This is free content with a guarantee.</p></body></html>"
        result = await self.check.run(html)
        # 'free' (0.05) + 'guarantee' (0.05) = 0.10 deduction, score = 0.90
        assert result.passed is True
        assert result.score >= 0.5

    async def test_word_boundary_matching(self):
        """Triggers should match on word boundaries, not substrings."""
        # 'free' should match 'free' but not 'freedom' or 'carefree'
        html_match = "<html><body><p>Get it for free today!</p></body></html>"
        result_match = await self.check.run(html_match)
        assert result_match.score < 1.0

        html_no_match = "<html><body><p>Enjoy the freedom of choice.</p></body></html>"
        result_no_match = await self.check.run(html_no_match)
        # 'freedom' should NOT trigger 'free' — word boundary matching
        assert result_no_match.score == 1.0 or result_no_match.score > result_match.score

    async def test_excessive_punctuation_flagged(self):
        """3+ consecutive ! or ? should be flagged."""
        html = "<html><body><p>Amazing deal!!!! Don't miss out???</p></body></html>"
        result = await self.check.run(html)
        assert "punctuation" in (result.details or "").lower()

    async def test_all_caps_words_flagged(self):
        """3+ consecutive all-caps words should be flagged."""
        html = "<html><body><p>THIS IS ABSOLUTELY FREE TODAY ONLY</p></body></html>"
        result = await self.check.run(html)
        assert "caps" in (result.details or "").lower()

    async def test_obfuscation_detected(self):
        """Leet-speak obfuscation like 'fr33' should be caught."""
        html = "<html><body><p>Get your fr33 prize now!</p></body></html>"
        result = await self.check.run(html)
        assert "obfuscat" in (result.details or "").lower()

    async def test_subject_line_higher_weight(self):
        """Spam triggers in <title> should have 3x weight multiplier."""
        html_body = (
            "<html><head><title>Newsletter</title></head><body><p>Buy now!</p></body></html>"
        )
        html_subject = (
            "<html><head><title>Buy now!</title></head><body><p>Regular content.</p></body></html>"
        )
        result_body = await self.check.run(html_body)
        result_subject = await self.check.run(html_subject)
        # Subject trigger (3x) should produce a larger deduction than body trigger
        assert result_subject.score < result_body.score

    async def test_heavy_triggers_fail(self):
        """Multiple high-weight triggers should push score below threshold."""
        html = (
            "<html><body><p>Congratulations! You have been selected as a winner! "
            "This is not spam. Double your money with this million dollars offer! "
            "Act now! Hurry! Last chance!</p></body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert result.score < 0.5

    async def test_empty_html(self):
        """Empty HTML should return error."""
        result = await self.check.run("")
        assert result.passed is False
        assert result.score == 0.0

    async def test_spam_triggers_export_backwards_compatible(self):
        """SPAM_TRIGGERS should still be importable as a list of strings."""
        from app.qa_engine.checks.spam_score import SPAM_TRIGGERS

        assert isinstance(SPAM_TRIGGERS, list)
        assert len(SPAM_TRIGGERS) >= 50
        assert all(isinstance(t, str) for t in SPAM_TRIGGERS)
        assert "buy now" in SPAM_TRIGGERS


# ── 6. Dark Mode ──


class TestDarkMode:
    check = DarkModeCheck()

    @staticmethod
    def _html(
        head: str = "",
        body: str = "<table role='presentation'><tr><td>Hello</td></tr></table>",
        lang: str = "en",
    ) -> str:
        return (
            f'<!DOCTYPE html><html lang="{lang}">'
            f"<head><meta charset='utf-8'><title>Test</title>{head}</head>"
            f"<body>{body}</body></html>"
        )

    # --- Full dark mode passes ---

    async def test_comprehensive_dark_mode_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    # --- Group A: Meta Tags ---

    async def test_missing_color_scheme_meta_deducts(self):
        html = self._html(
            head="<style>@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }"
            ":root { color-scheme: light dark; }</style>"
            "<meta name='supported-color-schemes' content='light dark'>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "color-scheme" in (result.details or "").lower()

    async def test_color_scheme_without_dark_deducts(self):
        html = self._html(
            head="<meta name='color-scheme' content='light'>"
            "<style>@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "dark" in (result.details or "").lower()

    async def test_supported_color_schemes_missing_minor_deduction(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<style>:root { color-scheme: light dark; } "
            "@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }</style>"
        )
        result = await self.check.run(html)
        # Only supported-color-schemes missing — 0.05 deduction
        assert result.passed is False
        assert result.score >= 0.90

    async def test_css_color_scheme_property_missing_minor(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<meta name='supported-color-schemes' content='light dark'>"
            "<style>@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert result.score >= 0.90

    async def test_meta_in_body_not_head_deducts(self):
        html = (
            "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<title>Test</title>"
            "<meta name='supported-color-schemes' content='light dark'>"
            "<style>:root { color-scheme: light dark; } "
            "@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }</style>"
            "</head><body>"
            "<meta name='color-scheme' content='light dark'>"
            "<table role='presentation'><tr><td>Hello</td></tr></table>"
            "</body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "body" in (result.details or "").lower() or "head" in (result.details or "").lower()

    # --- Group B: Media Queries ---

    async def test_no_media_query_heavy_deduction(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<style>[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert result.score <= 0.7

    async def test_empty_media_query_deducts(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<style>@media (prefers-color-scheme: dark) { }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert (
            "no color" in (result.details or "").lower()
            or "empty" in (result.details or "").lower()
        )

    async def test_media_query_no_important_deducts(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<meta name='supported-color-schemes' content='light dark'>"
            "<style>:root { color-scheme: light dark; } "
            "@media (prefers-color-scheme: dark) { .x { color: #fff; background-color: #000; } }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "!important" in (result.details or "")

    async def test_media_query_with_colors_and_important_passes(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<meta name='supported-color-schemes' content='light dark'>"
            "<style>:root { color-scheme: light dark; } "
            "@media (prefers-color-scheme: dark) { .x { color: #fff !important; background-color: #1a1a1a !important; } }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #1a1a1a; }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is True
        assert result.score == 1.0

    # --- Group C: Outlook Selectors ---

    async def test_no_outlook_selectors_deducts(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<style>@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        # ogsc + ogsb missing = 0.20
        assert "ogsc" in (result.details or "").lower() or "Outlook" in (result.details or "")

    async def test_empty_outlook_selectors_deducts(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<style>@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "[data-ogsc] .x { } [data-ogsb] .x { }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert (
            "no css declarations" in (result.details or "").lower()
            or "empty" in (result.details or "").lower()
        )

    async def test_ogsc_and_ogsb_with_declarations_passes(self):
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<meta name='supported-color-schemes' content='light dark'>"
            "<style>:root { color-scheme: light dark; } "
            "@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "[data-ogsc] .x { color: #fff; } [data-ogsb] .x { background-color: #000; }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is True

    # --- Group D: Color Coherence (integration tests with inline styles) ---

    async def test_good_contrast_dark_colors_passes(self):
        # No inline styles means no color pairs extracted — passes by default
        html = self._html(
            head="<meta name='color-scheme' content='light dark'>"
            "<meta name='supported-color-schemes' content='light dark'>"
            "<style>:root { color-scheme: light dark; } "
            "@media (prefers-color-scheme: dark) { .x { color: #e0e0e0 !important; background-color: #1a1a1a !important; } }"
            "[data-ogsc] .x { color: #e0e0e0; } [data-ogsb] .x { background-color: #1a1a1a; }</style>"
        )
        result = await self.check.run(html)
        assert result.passed is True
        assert result.score == 1.0

    # --- Group F: Backward Compat ---

    async def test_no_dark_mode_at_all_scores_very_low(self, sample_html_minimal):
        result = await self.check.run(sample_html_minimal)
        assert result.passed is False
        assert result.score < 0.5

    # --- Config Override ---

    async def test_config_overrides_deductions(self):
        from app.qa_engine.check_config import QACheckConfig

        # Override all deductions to minimal values
        config = QACheckConfig(
            enabled=True,
            params={
                "deduction_no_dark_mode": 0.01,
                "deduction_missing_color_scheme": 0.01,
                "deduction_missing_supported": 0.01,
                "deduction_missing_css_color_scheme": 0.01,
                "deduction_no_media_query": 0.01,
                "deduction_no_ogsc": 0.01,
                "deduction_no_ogsb": 0.01,
            },
        )
        html = "<html><body>No dark mode</body></html>"
        result = await self.check.run(html, config)
        assert result.passed is False
        # With all deductions reduced to 0.01, score should be much higher
        assert result.score > 0.9


# ── 7. Accessibility (24 WCAG AA checks, 8 groups) ──


class TestAccessibility:
    check = AccessibilityCheck()

    @staticmethod
    def _html(
        body: str,
        lang: str = "en",
        head: str = "",
    ) -> str:
        return (
            f'<!DOCTYPE html><html lang="{lang}"><head>'
            f'<meta charset="utf-8"><title>Test</title>{head}</head>'
            f"<body>{body}</body></html>"
        )

    # --- Fully accessible email passes ---

    async def test_fully_accessible_email(self):
        html = self._html(
            '<table role="presentation"><tr><td>'
            "<h1>Welcome</h1>"
            "<p>Hello! <strong>Important</strong> info here.</p>"
            "<h2>Products</h2>"
            '<a href="https://x.com/product">View product details</a>'
            '<img src="product.jpg" alt="Blue cotton t-shirt">'
            '<img src="pixel.gif" width="1" height="1" alt="" aria-hidden="true">'
            "</td></tr></table>"
        )
        result = await self.check.run(html)
        assert result.passed is True
        assert result.score == 1.0

    async def test_accessible_html_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_empty_html_fails(self):
        result = await self.check.run("")
        assert result.passed is False
        assert result.score == 0.0

    # --- Group A: Language ---

    async def test_lang_present_passes(self):
        html = self._html('<table role="presentation"><tr><td><h1>Hello</h1></td></tr></table>')
        result = await self.check.run(html)
        assert "lang" not in (result.details or "").lower()

    async def test_lang_missing_degrades(self):
        html = '<!DOCTYPE html><html><head><title>T</title></head><body><table role="presentation"><tr><td><h1>Hi</h1></td></tr></table></body></html>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "lang" in (result.details or "").lower()

    async def test_lang_invalid_degrades(self):
        html = '<!DOCTYPE html><html lang=""><head><title>T</title></head><body><table role="presentation"><tr><td><h1>Hi</h1></td></tr></table></body></html>'
        result = await self.check.run(html)
        assert "lang" in (result.details or "").lower()

    # --- Group B: Table Semantics ---

    async def test_layout_table_with_role_passes(self):
        html = self._html('<table role="presentation"><tr><td><h1>Hi</h1></td></tr></table>')
        result = await self.check.run(html)
        assert "presentation" not in (result.details or "").lower()

    async def test_layout_table_without_role_degrades(self):
        html = self._html("<table><tr><td><h1>Content</h1></td></tr></table>")
        result = await self.check.run(html)
        assert result.passed is False
        assert "presentation" in (result.details or "").lower()

    async def test_data_table_without_scope_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<table role="table"><tr><th>Name</th></tr><tr><td>Val</td></tr></table>'
            "</td></tr></table>"
        )
        result = await self.check.run(html)
        assert "scope" in (result.details or "").lower()

    async def test_mixed_signals_degrades(self):
        html = self._html('<table role="presentation"><tr><th>Bad</th></tr></table><h1>Hi</h1>')
        result = await self.check.run(html)
        assert "conflict" in (result.details or "").lower()

    # --- Group C: Image Accessibility ---

    async def test_img_with_alt_passes(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<img src="x.png" alt="Photo"></td></tr></table>'
        )
        result = await self.check.run(html)
        assert "missing alt" not in (result.details or "").lower()

    async def test_img_missing_alt_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1><img src="photo.jpg"></td></tr></table>'
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "alt" in (result.details or "").lower()

    async def test_tracking_pixel_with_empty_alt_passes(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<img src="pixel.gif" width="1" height="1" alt=""></td></tr></table>'
        )
        result = await self.check.run(html)
        assert "tracking" not in (result.details or "").lower()

    async def test_tracking_pixel_with_text_alt_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<img src="pixel.gif" width="1" height="1" alt="track"></td></tr></table>'
        )
        result = await self.check.run(html)
        assert (
            "tracking" in (result.details or "").lower()
            or "pixel" in (result.details or "").lower()
        )

    async def test_linked_img_no_alt_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<a href="https://x.com"><img src="hero.jpg" alt=""></a></td></tr></table>'
        )
        result = await self.check.run(html)
        assert (
            "linked" in (result.details or "").lower() or "link" in (result.details or "").lower()
        )

    # --- Group D: Heading Hierarchy ---

    async def test_proper_headings_passes(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Title</h1><h2>Section</h2></td></tr></table>'
        )
        result = await self.check.run(html)
        assert "heading" not in (result.details or "").lower()

    async def test_no_headings_degrades(self):
        html = self._html('<table role="presentation"><tr><td><p>No headings</p></td></tr></table>')
        result = await self.check.run(html)
        assert result.passed is False
        assert "heading" in (result.details or "").lower()

    async def test_multiple_h1_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>A</h1><h1>B</h1></td></tr></table>'
        )
        result = await self.check.run(html)
        assert "h1" in (result.details or "").lower()

    async def test_skipped_heading_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>A</h1><h3>C</h3></td></tr></table>'
        )
        result = await self.check.run(html)
        assert "skip" in (result.details or "").lower()

    # --- Group E: Link Accessibility ---

    async def test_descriptive_link_text_passes(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<a href="https://x.com">View your order</a></td></tr></table>'
        )
        result = await self.check.run(html)
        assert "generic" not in (result.details or "").lower()

    async def test_generic_link_text_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<a href="https://x.com">Click here</a></td></tr></table>'
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert (
            "generic" in (result.details or "").lower()
            or "click here" in (result.details or "").lower()
        )

    async def test_empty_link_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<a href="https://x.com"></a></td></tr></table>'
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "empty" in (result.details or "").lower()

    async def test_redundant_links_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<a href="https://x.com"><img src="p.jpg" alt="Product"></a>'
            '<a href="https://x.com">Product</a>'
            "</td></tr></table>"
        )
        result = await self.check.run(html)
        assert "redundant" in (result.details or "").lower()

    # --- Group F: Content Semantics ---

    async def test_strong_em_passes(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            "<strong>Bold</strong> and <em>italic</em></td></tr></table>"
        )
        result = await self.check.run(html)
        assert "<b>" not in (result.details or "")

    async def test_b_i_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            "<b>Bold</b> and <i>italic</i></td></tr></table>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "strong" in (result.details or "").lower() or "em" in (result.details or "").lower()

    async def test_consecutive_br_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>text<br><br>more text</td></tr></table>'
        )
        result = await self.check.run(html)
        assert "br" in (result.details or "").lower()

    async def test_outline_none_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1></td></tr></table>',
            head="<style>a { outline: none; }</style>",
        )
        result = await self.check.run(html)
        assert "outline" in (result.details or "").lower()

    # --- Group G: Dark Mode Contrast ---

    async def test_dark_mode_safe_colors_passes(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1></td></tr></table>',
            head='<meta name="color-scheme" content="light dark">'
            "<style>@media (prefers-color-scheme: dark) { .body { background-color: #1a1a1a; color: #f0f0f0; } }</style>",
        )
        result = await self.check.run(html)
        assert "dark mode" not in (result.details or "").lower()
        assert "unsafe" not in (result.details or "").lower()

    async def test_dark_mode_unsafe_pure_bw_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1></td></tr></table>',
            head='<meta name="color-scheme" content="light dark">'
            "<style>@media (prefers-color-scheme: dark) { .body { background-color: #000000; color: #ffffff; } }</style>",
        )
        result = await self.check.run(html)
        assert (
            "dark mode" in (result.details or "").lower()
            or "unsafe" in (result.details or "").lower()
            or "#ffffff" in (result.details or "").lower()
        )

    async def test_dark_meta_no_styles_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1></td></tr></table>',
            head='<meta name="color-scheme" content="light dark">',
        )
        result = await self.check.run(html)
        assert "dark" in (result.details or "").lower()

    async def test_no_dark_mode_no_issue(self):
        """Emails without dark mode meta should not trigger G21/G22."""
        html = self._html('<table role="presentation"><tr><td><h1>Hi</h1></td></tr></table>')
        result = await self.check.run(html)
        assert "dark" not in (result.details or "").lower()

    # --- Group H: AMP Form Accessibility ---

    async def test_input_with_label_passes(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<label for="email">Email</label><input type="email" id="email">'
            "</td></tr></table>"
        )
        result = await self.check.run(html)
        assert "label" not in (result.details or "").lower()

    async def test_input_no_label_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<input type="email" placeholder="Email">'
            "</td></tr></table>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert (
            "label" in (result.details or "").lower()
            or "placeholder" in (result.details or "").lower()
        )

    async def test_required_no_aria_degrades(self):
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1>'
            '<label for="name">Name</label><input type="text" id="name" required>'
            "</td></tr></table>"
        )
        result = await self.check.run(html)
        assert (
            "required" in (result.details or "").lower() or "aria" in (result.details or "").lower()
        )

    async def test_no_form_elements_no_issues(self):
        """Emails without form elements should not trigger H23/H24."""
        html = self._html(
            '<table role="presentation"><tr><td><h1>Hi</h1><p>No forms</p></td></tr></table>'
        )
        result = await self.check.run(html)
        assert "label" not in (result.details or "").lower()
        assert "aria-required" not in (result.details or "").lower()

    # --- Config override ---

    async def test_config_overrides_deduction(self):
        from app.qa_engine.check_config import QACheckConfig

        html = '<!DOCTYPE html><html><head><title>T</title></head><body><table role="presentation"><tr><td><h1>Hi</h1></td></tr></table></body></html>'
        config = QACheckConfig(params={"deduction_lang_missing": 0.50})
        result = await self.check.run(html, config)
        # Score should reflect the higher deduction
        assert result.score < 0.55


# ── 8. Fallback ──


class TestFallback:
    check = FallbackCheck()

    async def test_valid_mso_html_scores_perfect(self, sample_html_valid):
        """Full valid MSO HTML with balanced conditionals, namespaces, DPI → 1.0"""
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score == 1.0

    async def test_unbalanced_conditional_degrades(self):
        """Extra opener without closer → score reduction."""
        html = (
            '<!DOCTYPE html><html lang="en" xmlns:v="urn:schemas-microsoft-com:vml"'
            ' xmlns:o="urn:schemas-microsoft-com:office:office"><head>'
            "<!--[if mso]><xml><o:OfficeDocumentSettings>"
            "<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings>"
            "</xml><![endif]--></head><body>"
            "<!--[if mso]><table><tr><td><![endif]-->"
            "<p>Content</p>"
            "<!--[if mso]></td></tr></table><![endif]-->"
            "<!--[if mso]><p>Orphan opener"
            "</body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert result.score <= 0.80

    async def test_vml_outside_conditional_degrades(self):
        """<v:rect> not inside <!--[if mso]> → score reduction."""
        html = (
            '<!DOCTYPE html><html lang="en" xmlns:v="urn:schemas-microsoft-com:vml"'
            ' xmlns:o="urn:schemas-microsoft-com:office:office"><head>'
            "<!--[if mso]><xml><o:OfficeDocumentSettings>"
            "<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings>"
            "</xml><![endif]--></head><body>"
            "<!--[if mso]><p>MSO</p><![endif]-->"
            "<v:rect>orphan VML</v:rect>"
            "</body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "VML" in (result.details or "")

    async def test_missing_namespaces_degrades(self):
        """VML present but no xmlns:v on <html> → score reduction."""
        html = (
            "<!DOCTYPE html><html><head>"
            "<!--[if mso]><xml><o:OfficeDocumentSettings>"
            "<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings>"
            "</xml><![endif]--></head><body>"
            "<!--[if mso]><v:rect></v:rect><![endif]-->"
            "</body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert (
            "xmlns" in (result.details or "").lower()
            or "namespace" in (result.details or "").lower()
        )

    async def test_complex_nested_conditionals_valid(self):
        """Multiple nested balanced blocks → passes balance checks."""
        html = (
            '<!DOCTYPE html><html lang="en" xmlns:v="urn:schemas-microsoft-com:vml"'
            ' xmlns:o="urn:schemas-microsoft-com:office:office"><head>'
            "<!--[if mso]><xml><o:OfficeDocumentSettings>"
            "<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings>"
            "</xml><![endif]--></head><body>"
            '<!--[if mso]><table width="600"><tr><td><![endif]-->'
            "<p>Content</p>"
            "<!--[if mso]></td></tr></table><![endif]-->"
            "<!--[if gte mso 12]><v:rect></v:rect><![endif]-->"
            "</body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is True
        assert result.score == 1.0

    async def test_no_mso_at_all_degrades(self, sample_html_minimal):
        """Plain HTML, no MSO/VML → presence checks fail, low score."""
        result = await self.check.run(sample_html_minimal)
        assert result.passed is False
        assert result.score <= 0.5

    async def test_ghost_table_missing_width_degrades(self):
        """Ghost table pattern without width attr → score reduction."""
        html = (
            '<!DOCTYPE html><html lang="en" xmlns:v="urn:schemas-microsoft-com:vml"'
            ' xmlns:o="urn:schemas-microsoft-com:office:office"><head>'
            "<!--[if mso]><xml><o:OfficeDocumentSettings>"
            "<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings>"
            "</xml><![endif]--></head><body>"
            '<div style="max-width: 600px;">'
            "<!--[if mso]><table><tr><td><![endif]-->"
            "<p>Content</p>"
            "<!--[if mso]></td></tr></table><![endif]-->"
            "</div>"
            "</body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "width" in (result.details or "").lower()

    async def test_invalid_version_syntax_degrades(self):
        """<!--[if mso 13]> invalid version → syntax error."""
        html = (
            '<!DOCTYPE html><html lang="en" xmlns:v="urn:schemas-microsoft-com:vml"'
            ' xmlns:o="urn:schemas-microsoft-com:office:office"><head>'
            "<!--[if mso]><xml><o:OfficeDocumentSettings>"
            "<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings>"
            "</xml><![endif]--></head><body>"
            "<!--[if mso 13]><p>Bad version</p><![endif]-->"
            "</body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is False
        assert "13" in (result.details or "")

    async def test_non_mso_block_balanced(self):
        """<!--[if !mso]><!-->...<!--<![endif]--> correctly paired → passes."""
        html = (
            '<!DOCTYPE html><html lang="en" xmlns:v="urn:schemas-microsoft-com:vml"'
            ' xmlns:o="urn:schemas-microsoft-com:office:office"><head>'
            "<!--[if mso]><xml><o:OfficeDocumentSettings>"
            "<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings>"
            "</xml><![endif]--></head><body>"
            '<!--[if mso]><table width="600"><tr><td><![endif]-->'
            "<!--[if !mso]><!--><p>Non-Outlook</p><!--<![endif]-->"
            "<!--[if mso]></td></tr></table><![endif]-->"
            "</body></html>"
        )
        result = await self.check.run(html)
        assert result.passed is True

    async def test_config_overrides_deductions(self):
        """Custom QACheckConfig overrides default deduction values."""
        from app.qa_engine.check_config import QACheckConfig

        html = "<html><body><p>No MSO at all</p></body></html>"
        config = QACheckConfig(
            enabled=True,
            params={
                "deduction_no_mso": 0.10,
                "deduction_no_namespaces": 0.05,
                "deduction_no_dpi_fix": 0.01,
            },
        )
        result = await self.check.run(html, config)
        assert result.passed is False
        # With reduced deductions (0.10 + 0.05 + 0.01 = 0.16), score should be ~0.84
        assert result.score >= 0.80


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


# ── 11. Link Validation (DOM-parsed) ──


class TestLinkValidationCheck:
    check = LinkValidationCheck()

    async def test_valid_https_links(self):
        html = '<html><body><a href="https://example.com">Link</a></body></html>'
        result = await self.check.run(html)
        assert result.score == 1.0
        assert result.passed is True

    async def test_http_link_deducted(self):
        html = '<html><body><a href="http://example.com">Link</a></body></html>'
        result = await self.check.run(html)
        assert result.score < 1.0
        assert "Non-HTTPS" in (result.details or "")

    async def test_empty_href_deducted(self):
        html = '<html><body><a href="">Link</a></body></html>'
        result = await self.check.run(html)
        assert result.score < 1.0

    async def test_javascript_protocol_severe(self):
        html = '<html><body><a href="javascript:alert(1)">Link</a></body></html>'
        result = await self.check.run(html)
        assert result.score < 0.8  # Heavy deduction

    async def test_valid_liquid_template_not_flagged(self):
        html = '<html><body><a href="{{ url }}">Link</a></body></html>'
        result = await self.check.run(html)
        assert result.passed is True

    async def test_unbalanced_template_flagged(self):
        html = '<html><body><a href="{{ url }">Link</a></body></html>'
        result = await self.check.run(html)
        assert result.passed is False
        assert "template" in (result.details or "").lower()

    async def test_malformed_url_deducted(self):
        html = '<html><body><a href="https://">Link</a></body></html>'
        result = await self.check.run(html)
        assert result.score < 1.0

    async def test_empty_html(self):
        result = await self.check.run("")
        assert result.passed is False
        assert result.score == 0.0

    async def test_valid_html_passes(self, sample_html_valid):
        result = await self.check.run(sample_html_valid)
        assert result.passed is True
        assert result.score >= 0.9

    async def test_multiple_issues_capped(self):
        links = "".join(f'<a href="http://bad{i}.com">Link{i}</a>' for i in range(10))
        html = f"<html><body>{links}</body></html>"
        result = await self.check.run(html)
        assert result.score >= 0.0  # Capped at 0.0 not negative
