# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Unit tests for chaos profile transformations."""

from __future__ import annotations

import pytest

from app.qa_engine.chaos.composable import compose_profiles
from app.qa_engine.chaos.profiles import (
    CLASS_STRIP,
    DARK_MODE_INVERSION,
    GMAIL_CLIPPING,
    GMAIL_STYLE_STRIP,
    IMAGE_BLOCKED,
    MEDIA_QUERY_STRIP,
    MOBILE_NARROW,
    OUTLOOK_WORD_ENGINE,
    ChaosProfile,
)


def _wrap(body: str, head: str = "") -> str:
    return f"<!DOCTYPE html><html><head>{head}</head><body>{body}</body></html>"


# ── Gmail Style Strip ──


def test_gmail_style_strip_removes_style_blocks():
    html = _wrap("<p>text</p>", "<style>p { color: red; }</style>")
    result = GMAIL_STYLE_STRIP.apply(html)
    assert "<style>" not in result
    assert "<p>text</p>" in result


def test_gmail_style_strip_removes_stylesheet_links():
    html = _wrap("<p>text</p>", '<link rel="stylesheet" href="style.css">')
    result = GMAIL_STYLE_STRIP.apply(html)
    assert "stylesheet" not in result


def test_gmail_style_strip_preserves_inline_styles():
    html = _wrap('<p style="color: red;">text</p>')
    result = GMAIL_STYLE_STRIP.apply(html)
    assert 'style="color: red;"' in result


# ── Image Blocked ──


def test_image_blocked_replaces_src():
    html = _wrap('<img src="https://example.com/photo.jpg" alt="Photo">')
    result = IMAGE_BLOCKED.apply(html)
    assert "data:image/gif;base64," in result
    assert "example.com/photo.jpg" not in result


def test_image_blocked_preserves_alt():
    html = _wrap('<img src="photo.jpg" alt="My Photo">')
    result = IMAGE_BLOCKED.apply(html)
    assert 'alt="My Photo"' in result


# ── Dark Mode Inversion ──


def test_dark_mode_inversion_adds_attributes():
    html = _wrap("<p>text</p>")
    result = DARK_MODE_INVERSION.apply(html)
    assert "data-ogsc" in result
    assert "data-ogsb" in result


def test_dark_mode_inversion_adds_filter():
    html = _wrap("<p>text</p>")
    result = DARK_MODE_INVERSION.apply(html)
    assert "invert(1)" in result


# ── Outlook Word Engine ──


def test_outlook_word_engine_strips_flexbox():
    html = _wrap('<div style="display: flex; padding: 10px;">text</div>')
    result = OUTLOOK_WORD_ENGINE.apply(html)
    assert "display: flex" not in result.lower()
    assert "padding: 10px" in result


def test_outlook_word_engine_strips_grid():
    html = _wrap('<div style="display: grid; margin: 5px;">text</div>')
    result = OUTLOOK_WORD_ENGINE.apply(html)
    assert "display: grid" not in result.lower()
    assert "margin: 5px" in result


def test_outlook_word_engine_strips_custom_properties():
    html = _wrap('<div style="--brand-color: #fff; color: red;">text</div>')
    result = OUTLOOK_WORD_ENGINE.apply(html)
    assert "--brand-color" not in result
    assert "color: red" in result


# ── Gmail Clipping ──


def test_gmail_clipping_short_html_unchanged():
    html = _wrap("<p>short</p>")
    result = GMAIL_CLIPPING.apply(html)
    assert result == html


def test_gmail_clipping_truncates_at_boundary():
    # Create HTML larger than 102KB
    big_content = "<p>" + "x" * 120_000 + "</p>"
    html = _wrap(big_content)
    result = GMAIL_CLIPPING.apply(html)
    assert len(result.encode("utf-8")) <= 102_400
    assert result.endswith(">")


# ── Mobile Narrow ──


def test_mobile_narrow_injects_max_width():
    html = _wrap("<p>text</p>")
    result = MOBILE_NARROW.apply(html)
    assert "max-width: 375px" in result


# ── Class Strip ──


def test_class_strip_removes_all_classes():
    html = _wrap('<p class="text-lg font-bold">text</p><div class="wrapper">inner</div>')
    result = CLASS_STRIP.apply(html)
    assert "class=" not in result
    assert "<p>" in result


# ── Media Query Strip ──


def test_media_query_strip_removes_media_rules():
    css = "p { color: red; } @media (max-width: 600px) { p { color: blue; } }"
    html = _wrap("<p>text</p>", f"<style>{css}</style>")
    result = MEDIA_QUERY_STRIP.apply(html)
    assert "@media" not in result
    assert "color: red" in result


# ── Profile apply + composition ──


def test_profile_apply_chains_transforms():
    """A profile with 2 transforms applies both sequentially."""
    profile = ChaosProfile(
        name="double",
        description="strip styles + block images",
        transformations=(
            GMAIL_STYLE_STRIP.transformations[0],
            IMAGE_BLOCKED.transformations[0],
        ),
    )
    html = _wrap(
        '<img src="photo.jpg" alt="Photo">',
        "<style>p { color: red; }</style>",
    )
    result = profile.apply(html)
    assert "<style>" not in result
    assert "data:image/gif;base64," in result


def test_compose_profiles_stacks_all():
    composed = compose_profiles(GMAIL_STYLE_STRIP, IMAGE_BLOCKED)
    html = _wrap(
        '<img src="photo.jpg">',
        "<style>p { color: red; }</style>",
    )
    result = composed.apply(html)
    assert "<style>" not in result
    assert "data:image/gif;base64," in result
    assert "composed(" in composed.name


def test_compose_profiles_empty_raises():
    with pytest.raises(ValueError, match="At least one profile"):
        compose_profiles()


# ── Edge Case Tests ──


def test_outlook_word_engine_strips_var_references():
    html = _wrap('<div style="color: var(--brand); padding: 10px;">text</div>')
    result = OUTLOOK_WORD_ENGINE.apply(html)
    assert "var(" not in result
    assert "padding: 10px" in result


def test_gmail_clipping_exact_boundary():
    """HTML exactly at 102,400 bytes should be unchanged."""
    # Build HTML of exact size
    target = 102_400
    base = _wrap("")
    base_size = len(base.encode("utf-8"))
    pad_len = target - base_size - len("<p></p>")
    html = _wrap(f"<p>{'x' * pad_len}</p>")
    assert len(html.encode("utf-8")) == target
    result = GMAIL_CLIPPING.apply(html)
    assert result == html


def test_image_blocked_no_images_unchanged():
    html = _wrap("<p>No images here</p>")
    result = IMAGE_BLOCKED.apply(html)
    # BeautifulSoup may normalize whitespace, so compare content
    assert "<p>No images here</p>" in result
    assert "data:image/gif" not in result


def test_class_strip_preserves_other_attributes():
    html = _wrap('<div id="main" style="color: red;" class="wrapper">text</div>')
    result = CLASS_STRIP.apply(html)
    assert "class=" not in result
    assert 'id="main"' in result
    assert "color: red" in result
