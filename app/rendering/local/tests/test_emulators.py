"""Tests for email client sanitizer emulation (Gmail, Outlook.com + 5 new emulators)."""

from __future__ import annotations

from app.rendering.local.emulators import (
    EmailClientEmulator,
    EmulatorRule,
    get_emulator,
)
from app.rendering.local.profiles import CLIENT_PROFILES

# Minimal but realistic email HTML skeleton for tests
_EMAIL_SKELETON = (
    "<!DOCTYPE html>"
    '<html xmlns="http://www.w3.org/1999/xhtml">'
    "<head>"
    '<meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
    "{head_extra}"
    "</head>"
    "<body>"
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
    '<tr><td align="center">'
    '<table role="presentation" width="600" cellpadding="0" cellspacing="0">'
    "{body_content}"
    "</table>"
    "</td></tr></table>"
    "</body></html>"
)


def _email(body: str, head: str = "") -> str:
    return _EMAIL_SKELETON.format(head_extra=head, body_content=body)


# ── Existing Gmail tests ──


class TestGmailClassRewrite:
    """Gmail class name prefixing."""

    def test_rewrites_class_names(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = _email('<tr><td class="header main" style="padding:10px;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "m_" in result
        assert "header" in result  # class name preserved, just prefixed

    def test_consistent_prefix(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = _email('<tr><td class="foo">A</td></tr><tr><td class="bar">B</td></tr>')
        result = emulator.transform(html)
        classes = []
        for part in result.split('class="')[1:]:
            classes.append(part.split('"')[0])
        prefixes = [c.split("_")[1] for c in classes[0].split()]
        assert len(set(prefixes)) == 1


class TestGmailStyleStrip:
    """Gmail strips <style> blocks."""

    def test_strips_style_tags(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = _email(
            "<tr><td>Hello</td></tr>",
            head="<style>.foo { color: red; }</style>",
        )
        result = emulator.transform(html)
        assert "<style>" not in result
        assert "color: red" not in result


class TestGmailFormStrip:
    """Gmail strips form elements."""

    def test_strips_form_elements(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = _email(
            "<tr><td>"
            '<form action="/submit"><input type="text"><button>Go</button></form>'
            "<p>After</p>"
            "</td></tr>"
        )
        result = emulator.transform(html)
        assert "<form" not in result
        assert "<input" not in result
        assert "After" in result


class TestOutlookCSSStrip:
    """Outlook.com strips unsupported CSS."""

    def test_strips_background_image(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        html = _email(
            '<tr><td style="background-image: url(hero.jpg); color: red;">Hello</td></tr>'
        )
        result = emulator.transform(html)
        assert "background-image" not in result
        assert "color" in result

    def test_strips_box_shadow(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        html = _email('<tr><td style="box-shadow: 0 2px 4px #000; padding: 10px;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "box-shadow" not in result


class TestOutlookShorthandRewrite:
    """Outlook.com rewrites shorthand to longhand."""

    def test_expands_margin_shorthand(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        html = _email('<tr><td style="margin: 10px 20px;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "margin-top" in result
        assert "margin-right" in result


class TestEmulatorRoundTrip:
    """Emulator produces valid HTML."""

    def test_gmail_valid_html(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = _email(
            '<tr><td class="test" style="padding: 10px;">Hello</td></tr>',
            head="<style>.test { color: blue; }</style>",
        )
        result = emulator.transform(html)
        assert "<html" in result
        assert "<body" in result
        assert "Hello" in result

    def test_outlook_valid_html(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        html = _email(
            '<tr><td style="box-shadow: 1px 1px 3px #ccc; margin: 10px 20px;">Content</td></tr>'
        )
        result = emulator.transform(html)
        assert "Content" in result
        assert "<body" in result


class TestTransformOrdering:
    """Transform rules are applied in defined order."""

    def test_ordering_preserved(self) -> None:
        order: list[str] = []

        def make_rule(name: str) -> EmulatorRule:
            def transform(html: str) -> str:
                order.append(name)
                return html

            return EmulatorRule(name=name, transform=transform)

        emulator = EmailClientEmulator(
            client_id="test",
            rules=[make_rule("first"), make_rule("second"), make_rule("third")],
        )
        emulator.transform("<table><tr><td>test</td></tr></table>")
        assert order == ["first", "second", "third"]


# ── Yahoo Mail tests ──


class TestYahooClassRewrite:
    def test_rewrites_class_names_with_yiv_prefix(self) -> None:
        emulator = get_emulator("yahoo_web")
        assert emulator is not None
        html = _email('<tr><td class="hero main" style="padding:20px;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "yiv" in result
        assert "hero" in result  # class name preserved, just prefixed

    def test_strips_unsupported_css(self) -> None:
        emulator = get_emulator("yahoo_web")
        assert emulator is not None
        html = _email('<tr><td style="position: absolute; color: red;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "position" not in result
        assert "color" in result

    def test_enforces_max_width(self) -> None:
        emulator = get_emulator("yahoo_web")
        assert emulator is not None
        html = _email("<tr><td>Hello</td></tr>")
        result = emulator.transform(html)
        assert "800px" in result


class TestYahooMobileStripsStyleBlocks:
    def test_mobile_strips_style_blocks(self) -> None:
        emulator = get_emulator("yahoo_mobile")
        assert emulator is not None
        html = _email(
            "<tr><td>Hello</td></tr>",
            head="<style>.foo { color: red; }</style>",
        )
        result = emulator.transform(html)
        assert "<style>" not in result

    def test_web_preserves_style_blocks(self) -> None:
        emulator = get_emulator("yahoo_web")
        assert emulator is not None
        html = _email(
            "<tr><td>Hello</td></tr>",
            head="<style>.foo { color: red; }</style>",
        )
        result = emulator.transform(html)
        assert "color: red" in result


# ── Samsung Mail tests ──


class TestSamsungEmulator:
    def test_strips_blend_modes(self) -> None:
        emulator = get_emulator("samsung_mail")
        assert emulator is not None
        html = _email('<tr><td style="mix-blend-mode: multiply; color: red;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "mix-blend-mode" not in result
        assert "color" in result

    def test_image_proxy_appends_param(self) -> None:
        emulator = get_emulator("samsung_mail")
        assert emulator is not None
        html = _email(
            '<tr><td><img src="https://example.com/hero.jpg" alt="Hero" width="600"></td></tr>'
        )
        result = emulator.transform(html)
        assert "samsung_proxy=1" in result

    def test_image_proxy_handles_existing_query(self) -> None:
        emulator = get_emulator("samsung_mail")
        assert emulator is not None
        html = _email(
            '<tr><td><img src="https://example.com/hero.jpg?w=600" alt="Hero" width="600"></td></tr>'
        )
        result = emulator.transform(html)
        assert "&samsung_proxy=1" in result

    def test_dark_mode_inject_when_no_explicit_dark(self) -> None:
        emulator = get_emulator("samsung_mail")
        assert emulator is not None
        html = _email("<tr><td>Hello</td></tr>")
        result = emulator.transform(html)
        assert "color-scheme" in result or "background-color" in result

    def test_dark_mode_skips_when_explicit(self) -> None:
        emulator = get_emulator("samsung_mail")
        assert emulator is not None
        html = _email(
            "<tr><td>Hello</td></tr>",
            head="<style>@media (prefers-color-scheme: dark) { body { background: #000; } }</style>",
        )
        result = emulator.transform(html)
        # Should NOT inject forced dark mode since explicit styles exist
        assert "color-scheme" not in result.split("<style>")[0]


# ── Outlook Desktop (Word engine) tests ──


class TestOutlookDesktopEmulator:
    def test_strips_flex_display(self) -> None:
        emulator = get_emulator("outlook_desktop")
        assert emulator is not None
        html = _email('<tr><td style="display: flex; color: red;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "display" not in result or "flex" not in result
        assert "color" in result

    def test_strips_border_radius(self) -> None:
        emulator = get_emulator("outlook_desktop")
        assert emulator is not None
        html = _email('<tr><td style="border-radius: 8px; padding: 10px;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "border-radius" not in result

    def test_expands_margin_shorthand(self) -> None:
        emulator = get_emulator("outlook_desktop")
        assert emulator is not None
        html = _email('<tr><td style="margin: 10px 20px;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "margin-top" in result

    def test_processes_mso_conditionals(self) -> None:
        emulator = get_emulator("outlook_desktop")
        assert emulator is not None
        html = (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            "<tr><td>Before</td></tr></table>"
            '<!--[if mso]><table role="presentation" width="600"><tr><td><![endif]-->'
            '<table role="presentation" cellpadding="0" cellspacing="0">'
            "<tr><td>Content</td></tr></table>"
            "<!--[if mso]></td></tr></table><![endif]-->"
            '<table role="presentation"><tr><td>After</td></tr></table>'
        )
        result = emulator.transform(html)
        assert 'role="presentation"' in result
        assert "<!--[if mso]>" not in result

    def test_removes_not_mso_blocks(self) -> None:
        emulator = get_emulator("outlook_desktop")
        assert emulator is not None
        html = _email(
            "<tr><td>Before</td></tr>"
            '</table><!--[if !mso]><!--><table class="modern-only"><tr><td>Flex</td></tr></table><!--<![endif]--><table>'
            "<tr><td>After</td></tr>"
        )
        result = emulator.transform(html)
        assert "modern-only" not in result
        assert "Before" in result
        assert "After" in result

    def test_injects_table_width(self) -> None:
        emulator = get_emulator("outlook_desktop")
        assert emulator is not None
        html = _email("<tr><td>Hello</td></tr>")
        result = emulator.transform(html)
        assert 'width="600"' in result


# ── Thunderbird tests ──


class TestThunderbirdEmulator:
    def test_strips_position_sticky(self) -> None:
        emulator = get_emulator("thunderbird")
        assert emulator is not None
        html = _email('<tr><td style="position: sticky; top: 0; color: red;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "sticky" not in result
        assert "color" in result

    def test_preserves_style_blocks(self) -> None:
        emulator = get_emulator("thunderbird")
        assert emulator is not None
        html = _email(
            "<tr><td>Hello</td></tr>",
            head="<style>.foo { color: red; }</style>",
        )
        result = emulator.transform(html)
        assert "<style>" in result
        assert "color: red" in result


# ── Android Gmail tests ──


class TestAndroidGmailEmulator:
    def test_inherits_gmail_style_strip(self) -> None:
        emulator = get_emulator("android_gmail")
        assert emulator is not None
        html = _email(
            "<tr><td>Hello</td></tr>",
            head="<style>.foo { color: red; }</style>",
        )
        result = emulator.transform(html)
        assert "<style>" not in result

    def test_inherits_gmail_class_rewrite(self) -> None:
        emulator = get_emulator("android_gmail")
        assert emulator is not None
        html = _email('<tr><td class="header" style="padding:10px;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "m_" in result

    def test_injects_viewport_meta(self) -> None:
        emulator = get_emulator("android_gmail")
        assert emulator is not None
        html = _email("<tr><td>Hello</td></tr>")
        result = emulator.transform(html)
        assert "viewport" in result
        assert "width=device-width" in result

    def test_adds_dark_mode_attributes(self) -> None:
        emulator = get_emulator("android_gmail")
        assert emulator is not None
        html = _email("<tr><td>Hello</td></tr>")
        result = emulator.transform(html)
        assert "data-ogsc" in result

    def test_strips_amp(self) -> None:
        emulator = get_emulator("android_gmail")
        assert emulator is not None
        html = (
            '<html ⚡4email xmlns="http://www.w3.org/1999/xhtml">'
            "<head></head><body>"
            '<table role="presentation"><tr><td>AMP</td></tr></table>'
            "</body></html>"
        )
        result = emulator.transform(html)
        assert "⚡4email" not in result


# ── Profile integration tests ──


class TestProfileEmulatorIntegration:
    """All profiles reference valid emulators."""

    def test_gmail_profile_has_emulator(self) -> None:
        profile = CLIENT_PROFILES["gmail_web"]
        assert profile.emulator_id == "gmail_web"
        emulator = get_emulator(profile.emulator_id)
        assert emulator is not None

    def test_outlook_web_profile_has_emulator(self) -> None:
        profile = CLIENT_PROFILES["outlook_web"]
        assert profile.emulator_id == "outlook_web"
        emulator = get_emulator(profile.emulator_id)
        assert emulator is not None

    def test_yahoo_web_profile(self) -> None:
        profile = CLIENT_PROFILES["yahoo_web"]
        assert profile.emulator_id == "yahoo_web"
        assert get_emulator(profile.emulator_id) is not None

    def test_yahoo_mobile_profile(self) -> None:
        profile = CLIENT_PROFILES["yahoo_mobile"]
        assert profile.emulator_id == "yahoo_mobile"
        assert get_emulator(profile.emulator_id) is not None

    def test_samsung_mail_profile(self) -> None:
        profile = CLIENT_PROFILES["samsung_mail"]
        assert profile.emulator_id == "samsung_mail"
        assert get_emulator(profile.emulator_id) is not None

    def test_outlook_desktop_profile(self) -> None:
        profile = CLIENT_PROFILES["outlook_desktop"]
        assert profile.emulator_id == "outlook_desktop"
        assert get_emulator(profile.emulator_id) is not None

    def test_thunderbird_profile(self) -> None:
        profile = CLIENT_PROFILES["thunderbird"]
        assert profile.emulator_id == "thunderbird"
        assert profile.browser == "ff"
        assert get_emulator(profile.emulator_id) is not None

    def test_android_gmail_profile(self) -> None:
        profile = CLIENT_PROFILES["android_gmail"]
        assert profile.emulator_id == "android_gmail"
        assert get_emulator(profile.emulator_id) is not None


# ── Regression tests — existing emulators unchanged ──


class TestExistingEmulatorRegression:
    """Existing Gmail/Outlook.com emulators are not broken by new code."""

    def test_gmail_still_has_6_rules(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        assert len(emulator.rules) == 6

    def test_outlook_web_still_has_3_rules(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        assert len(emulator.rules) == 3

    def test_gmail_transform_unchanged(self) -> None:
        """Gmail emulator produces expected output for known input."""
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = _email('<tr><td class="test" style="display: flex; color: red;">Hello</td></tr>')
        result = emulator.transform(html)
        assert "m_" in result  # class rewriting
        assert "flex" not in result  # unsupported CSS stripped
        assert "color" in result  # supported CSS preserved
