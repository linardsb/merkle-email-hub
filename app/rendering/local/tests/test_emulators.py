"""Tests for 24B.4 — Gmail & Outlook.com Sanitizer Emulation."""

from __future__ import annotations

import pytest

from app.rendering.local.emulators import (
    EmailClientEmulator,
    EmulatorRule,
    get_emulator,
)
from app.rendering.local.profiles import CLIENT_PROFILES
from app.rendering.local.runner import _prepare_html


class TestGmailClassRewrite:
    """Gmail class name prefixing."""

    def test_rewrites_class_names(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = '<div class="header main">Hello</div>'
        result = emulator.transform(html)
        assert "m_" in result
        assert "header" not in result.split('class="')[1].split('"')[0].split("m_")[0]

    def test_consistent_prefix(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = '<div class="foo">A</div><div class="bar">B</div>'
        result = emulator.transform(html)
        # Both classes should have the same prefix
        classes = []
        for part in result.split('class="')[1:]:
            classes.append(part.split('"')[0])
        prefixes = [c.split("_")[1] for c in classes[0].split()]
        assert len(set(prefixes)) == 1  # Same prefix


class TestGmailStyleStrip:
    """Gmail strips <style> blocks."""

    def test_strips_style_tags(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = '<html><head><style>.foo { color: red; }</style></head><body><p>Hello</p></body></html>'
        result = emulator.transform(html)
        assert "<style>" not in result
        assert "color: red" not in result


class TestGmailFormStrip:
    """Gmail strips form elements."""

    def test_strips_form_elements(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = '<form action="/submit"><input type="text"><button>Go</button></form><p>After</p>'
        result = emulator.transform(html)
        assert "<form" not in result
        assert "<input" not in result
        assert "<p>After</p>" in result


class TestOutlookCSSStrip:
    """Outlook.com strips unsupported CSS."""

    def test_strips_background_image(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        html = '<div style="background-image: url(hero.jpg); color: red;">Hello</div>'
        result = emulator.transform(html)
        assert "background-image" not in result
        assert "color: red" in result or "color:red" in result

    def test_strips_box_shadow(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        html = '<div style="box-shadow: 0 2px 4px #000; padding: 10px;">Hello</div>'
        result = emulator.transform(html)
        assert "box-shadow" not in result


class TestOutlookShorthandRewrite:
    """Outlook.com rewrites shorthand to longhand."""

    def test_expands_margin_shorthand(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        html = '<div style="margin: 10px 20px;">Hello</div>'
        result = emulator.transform(html)
        assert "margin-top" in result
        assert "margin-right" in result


class TestEmulatorRoundTrip:
    """Emulator produces valid HTML."""

    def test_gmail_valid_html(self) -> None:
        emulator = get_emulator("gmail_web")
        assert emulator is not None
        html = """<!DOCTYPE html>
<html><head><style>.test { color: blue; }</style></head>
<body><table><tr><td class="test" style="padding: 10px;">Hello</td></tr></table></body></html>"""
        result = emulator.transform(html)
        assert "<html>" in result
        assert "<body>" in result
        assert "Hello" in result

    def test_outlook_valid_html(self) -> None:
        emulator = get_emulator("outlook_web")
        assert emulator is not None
        html = """<!DOCTYPE html>
<html><head></head><body><div style="box-shadow: 1px 1px 3px #ccc; margin: 10px 20px;">Content</div></body></html>"""
        result = emulator.transform(html)
        assert "Content" in result
        assert "<body" in result


class TestProfileEmulatorIntegration:
    """Profile references correct emulator."""

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


class TestTransformOrdering:
    """Transform rules are applied in defined order."""

    def test_ordering_preserved(self) -> None:
        """Rules must be applied in the order they're defined."""
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
        emulator.transform("<p>test</p>")
        assert order == ["first", "second", "third"]
