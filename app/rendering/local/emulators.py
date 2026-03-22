"""Email client sanitizer emulation.

Replicates the HTML/CSS transformations that email clients apply
when rendering email. These emulators produce more realistic previews
than simple Playwright profiles alone.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Types ──


@dataclass(frozen=True)
class EmulatorRule:
    """A single transformation rule applied by an email client emulator."""

    name: str
    transform: Callable[[str], str]
    description: str = ""
    confidence_impact: float = 0.0  # 0.0 = no impact, 1.0 = full confidence loss


class EmailClientEmulator:
    """Applies a chain of transformation rules to emulate client behavior."""

    def __init__(self, client_id: str, rules: list[EmulatorRule]) -> None:
        self.client_id = client_id
        self.rules = rules

    def transform(self, html: str) -> str:
        """Apply all rules in order."""
        result = html
        for rule in self.rules:
            result = rule.transform(result)
        return result


# ── Gmail Emulator Rules ──

_STYLE_TAG_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_LINK_TAG_RE = re.compile(r"<link\b[^>]*rel=[\"']stylesheet[\"'][^>]*/?>", re.IGNORECASE)
_CLASS_ATTR_RE = re.compile(r'\bclass\s*=\s*"([^"]*)"', re.IGNORECASE)
# Note: Regex-based HTML stripping is an approximation for preview fidelity,
# NOT a security boundary. Use nh3 for actual XSS sanitization.
_FORM_ELEMENTS_RE = re.compile(
    r"<(?:form|input|button|select|textarea|svg|math)\b[^>]*>.*?</(?:form|input|button|select|textarea|svg|math)>|"
    r"<(?:form|input|button|select|textarea|svg|math)\b[^>]*/?>",
    re.DOTALL | re.IGNORECASE,
)
_GMAIL_UNSUPPORTED_CSS_RE = re.compile(
    r"(position|float)\s*:[^;]+;?|"
    r"display\s*:\s*(?:flex|grid|inline-flex|inline-grid)[^;]*;?",
    re.IGNORECASE,
)
_INLINE_STYLE_RE = re.compile(r'(style\s*=\s*")([^"]*)"', re.IGNORECASE)
_BODY_TAG_RE = re.compile(r"(<body\b[^>]*)(>)", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"(<html\b[^>]*)(>)", re.IGNORECASE)
_HEAD_TAG_RE = re.compile(r"(<head\b[^>]*>)", re.IGNORECASE)
_TABLE_TAG_RE = re.compile(r"(<table\b)([^>]*>)", re.IGNORECASE)
_STYLE_PREPEND_RE = re.compile(r'(style\s*=\s*")', re.IGNORECASE)
_SEMICOLON_CLEANUP_RE = re.compile(r";\s*;+")


def _gmail_strip_style_blocks(html: str) -> str:
    """Remove all <style> tags (Gmail strips embedded CSS)."""
    return _STYLE_TAG_RE.sub("", html)


def _gmail_strip_link_tags(html: str) -> str:
    """Remove <link rel="stylesheet"> tags."""
    return _LINK_TAG_RE.sub("", html)


def _gmail_rewrite_classes(html: str) -> str:
    """Prefix class names with random ID (Gmail behavior: .foo -> .m_123_foo)."""
    prefix = "m_" + hashlib.md5(html[:200].encode(), usedforsecurity=False).hexdigest()[:6] + "_"

    def _rewrite(m: re.Match[str]) -> str:
        classes = m.group(1)
        rewritten = " ".join(prefix + cls for cls in classes.split() if cls)
        return f'class="{rewritten}"'

    return _CLASS_ATTR_RE.sub(_rewrite, html)


def _gmail_strip_unsupported_inline_css(html: str) -> str:
    """Remove position, float, display:flex/grid from inline style="" attrs."""

    def _strip(m: re.Match[str]) -> str:
        prefix = m.group(1)
        style = m.group(2)
        cleaned = _GMAIL_UNSUPPORTED_CSS_RE.sub("", style)
        # Clean up leftover semicolons
        cleaned = _SEMICOLON_CLEANUP_RE.sub(";", cleaned).strip("; ")
        return f'{prefix}{cleaned}"'

    return _INLINE_STYLE_RE.sub(_strip, html)


def _gmail_strip_form_elements(html: str) -> str:
    """Remove <form>, <input>, <button>, <select>, <svg>, <math> elements."""
    return _FORM_ELEMENTS_RE.sub("", html)


def _gmail_enforce_body_max_width(html: str) -> str:
    """Inject max-width: 680px on body."""
    match = _BODY_TAG_RE.search(html)
    if match:
        tag = match.group(1)
        if 'style="' in tag.lower():
            html = _BODY_TAG_RE.sub(
                lambda m: (
                    _STYLE_PREPEND_RE.sub(
                        r"\1max-width:680px;margin:0 auto;",
                        m.group(1),
                    )
                    + m.group(2)
                ),
                html,
                count=1,
            )
        else:
            html = _BODY_TAG_RE.sub(r'\1 style="max-width:680px;margin:0 auto;"\2', html, count=1)
    return html


# ── Outlook.com Emulator Rules ──

_OUTLOOK_UNSUPPORTED_RE = re.compile(
    r"background-image\s*:[^;]+;?|"
    r"box-shadow\s*:[^;]+;?|"
    r"text-shadow\s*:[^;]+;?",
    re.IGNORECASE,
)

_BORDER_RADIUS_RE = re.compile(r"border-radius\s*:[^;]+;?", re.IGNORECASE)

_SHORTHAND_MARGIN_RE = re.compile(
    r"margin\s*:\s*(\S+?)(?:\s+(\S+?))?(?:\s+(\S+?))?(?:\s+(\S+?))?\s*(?:;|$)",
    re.IGNORECASE,
)
_SHORTHAND_PADDING_RE = re.compile(
    r"padding\s*:\s*(\S+?)(?:\s+(\S+?))?(?:\s+(\S+?))?(?:\s+(\S+?))?\s*(?:;|$)",
    re.IGNORECASE,
)


def _outlook_strip_unsupported_css(html: str) -> str:
    """Remove background-image, box-shadow, text-shadow from inline styles."""

    def _strip(m: re.Match[str]) -> str:
        prefix = m.group(1)
        style = m.group(2)
        cleaned = _OUTLOOK_UNSUPPORTED_RE.sub("", style)
        cleaned = _BORDER_RADIUS_RE.sub("", cleaned)
        cleaned = _SEMICOLON_CLEANUP_RE.sub(";", cleaned).strip("; ")
        return f'{prefix}{cleaned}"'

    return _INLINE_STYLE_RE.sub(_strip, html)


def _expand_shorthand(match: re.Match[str], prop: str) -> str:
    """Expand margin/padding shorthand to longhand."""
    top = match.group(1)
    right = match.group(2) or top
    bottom = match.group(3) or top
    left = match.group(4) or right
    return f"{prop}-top:{top};{prop}-right:{right};{prop}-bottom:{bottom};{prop}-left:{left};"


def _outlook_rewrite_shorthand(html: str) -> str:
    """Convert margin/padding shorthand to longhand in inline styles."""

    def _rewrite(m: re.Match[str]) -> str:
        prefix = m.group(1)
        style = m.group(2)
        style = _SHORTHAND_MARGIN_RE.sub(lambda s: _expand_shorthand(s, "margin"), style)
        style = _SHORTHAND_PADDING_RE.sub(lambda s: _expand_shorthand(s, "padding"), style)
        return f'{prefix}{style}"'

    return _INLINE_STYLE_RE.sub(_rewrite, html)


def _outlook_inject_dark_mode_attrs(html: str) -> str:
    """Add [data-ogsc]/[data-ogsb] to simulate Outlook.com dark mode rewriting."""
    # Outlook.com adds data-ogsc (color) and data-ogsb (background) attributes
    # to elements when dark mode is active. This simulates that behavior
    # so previews show realistic dark mode transformations.
    match = _BODY_TAG_RE.search(html)
    if match:
        html = _BODY_TAG_RE.sub(r"\1 data-ogsc data-ogsb\2", html, count=1)
    return html


# ── Yahoo Mail Emulator Rules ──

_YAHOO_UNSUPPORTED_CSS_RE = re.compile(
    r"position\s*:[^;]+;?|"
    r"float\s*:[^;]+;?|"
    r"overflow\s*:[^;]+;?|"
    r"clip-path\s*:[^;]+;?",
    re.IGNORECASE,
)


def _yahoo_strip_style_blocks(html: str) -> str:
    """Strip <style> blocks (Yahoo mobile behavior)."""
    return _STYLE_TAG_RE.sub("", html)


def _yahoo_strip_unsupported_css(html: str) -> str:
    """Remove position, float, overflow, clip-path from inline styles."""

    def _strip(m: re.Match[str]) -> str:
        prefix = m.group(1)
        style = m.group(2)
        cleaned = _YAHOO_UNSUPPORTED_CSS_RE.sub("", style)
        cleaned = _SEMICOLON_CLEANUP_RE.sub(";", cleaned).strip("; ")
        return f'{prefix}{cleaned}"'

    return _INLINE_STYLE_RE.sub(_strip, html)


def _yahoo_rewrite_classes(html: str) -> str:
    """Prefix classes with yiv + hash (Yahoo behavior: .foo -> .yiv1234567890foo)."""
    prefix = "yiv" + hashlib.md5(html[:200].encode(), usedforsecurity=False).hexdigest()[:10]

    def _rewrite(m: re.Match[str]) -> str:
        classes = m.group(1)
        rewritten = " ".join(prefix + cls for cls in classes.split() if cls)
        return f'class="{rewritten}"'

    return _CLASS_ATTR_RE.sub(_rewrite, html)


def _yahoo_enforce_max_width(html: str) -> str:
    """Inject max-width: 800px on body."""
    match = _BODY_TAG_RE.search(html)
    if match:
        tag = match.group(1)
        if 'style="' in tag.lower():
            html = _BODY_TAG_RE.sub(
                lambda m: (
                    _STYLE_PREPEND_RE.sub(
                        r"\1max-width:800px;margin:0 auto;",
                        m.group(1),
                    )
                    + m.group(2)
                ),
                html,
                count=1,
            )
        else:
            html = _BODY_TAG_RE.sub(r'\1 style="max-width:800px;margin:0 auto;"\2', html, count=1)
    return html


# ── Samsung Mail Emulator Rules ──

_SAMSUNG_UNSUPPORTED_CSS_RE = re.compile(
    r"background-blend-mode\s*:[^;]+;?|"
    r"mix-blend-mode\s*:[^;]+;?|"
    r"filter\s*:[^;]+;?|"
    r"backdrop-filter\s*:[^;]+;?|"
    r"clip-path\s*:[^;]+;?",
    re.IGNORECASE,
)

_IMG_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc\s*=\s*")([^"]+)(")', re.IGNORECASE)


def _samsung_strip_unsupported_css(html: str) -> str:
    """Remove blend modes, filter, backdrop-filter, clip-path from inline styles."""

    def _strip(m: re.Match[str]) -> str:
        prefix = m.group(1)
        style = m.group(2)
        cleaned = _SAMSUNG_UNSUPPORTED_CSS_RE.sub("", style)
        cleaned = _SEMICOLON_CLEANUP_RE.sub(";", cleaned).strip("; ")
        return f'{prefix}{cleaned}"'

    return _INLINE_STYLE_RE.sub(_strip, html)


def _samsung_image_proxy(html: str) -> str:
    """Append ?samsung_proxy=1 to <img src> URLs."""

    def _rewrite(m: re.Match[str]) -> str:
        prefix = m.group(1)
        url = m.group(2)
        suffix = m.group(3)
        separator = "&" if "?" in url else "?"
        return f"{prefix}{url}{separator}samsung_proxy=1{suffix}"

    return _IMG_SRC_RE.sub(_rewrite, html)


def _samsung_dark_mode_inject(html: str) -> str:
    """Inject auto-dark-mode when no explicit prefers-color-scheme exists."""
    if "prefers-color-scheme" in html:
        return html

    # Add color-scheme on <html>
    html = _HTML_TAG_RE.sub(r'\1 style="color-scheme:dark;"\2', html, count=1)

    # Add dark background/foreground on <body>
    match = _BODY_TAG_RE.search(html)
    if match:
        tag = match.group(1)
        if 'style="' in tag.lower():
            html = _BODY_TAG_RE.sub(
                lambda m: (
                    _STYLE_PREPEND_RE.sub(
                        r"\1background-color:#1e1e1e;color:#ffffff;",
                        m.group(1),
                    )
                    + m.group(2)
                ),
                html,
                count=1,
            )
        else:
            html = _BODY_TAG_RE.sub(
                r'\1 style="background-color:#1e1e1e;color:#ffffff;"\2', html, count=1
            )
    return html


# ── Outlook Desktop (Word Engine) Emulator Rules ──

_OUTLOOK_WORD_UNSUPPORTED_RE = re.compile(
    r"display\s*:\s*(?:flex|grid|inline-flex|inline-grid)[^;]*;?|"
    r"position\s*:\s*(?:fixed|sticky|absolute|relative)[^;]*;?|"
    r"float\s*:[^;]+;?|"
    r"box-shadow\s*:[^;]+;?|"
    r"text-shadow\s*:[^;]+;?|"
    r"border-radius\s*:[^;]+;?|"
    r"background-image\s*:[^;]+;?|"
    r"opacity\s*:[^;]+;?|"
    r"transform\s*:[^;]+;?|"
    r"transition\s*:[^;]+;?|"
    r"animation[^:]*\s*:[^;]+;?|"
    r"filter\s*:[^;]+;?|"
    r"overflow\s*:[^;]+;?|"
    r"clip-path\s*:[^;]+;?|"
    r"object-fit\s*:[^;]+;?",
    re.IGNORECASE,
)

_MSO_CONDITIONAL_RE = re.compile(
    r"<!--\[if\s+mso\]>(.*?)<!\[endif\]-->",
    re.DOTALL | re.IGNORECASE,
)
_NOT_MSO_CONDITIONAL_RE = re.compile(
    r"<!--\[if\s+!mso\]><!-->(.*?)<!--<!\[endif\]-->",
    re.DOTALL | re.IGNORECASE,
)

_SHORTHAND_BORDER_RE = re.compile(
    r"border\s*:\s*(\S+)\s+(\S+)\s+(\S+)\s*(?:;|$)",
    re.IGNORECASE,
)
_SHORTHAND_FONT_RE = re.compile(
    r"font\s*:\s*(?:(?:italic|oblique|normal)\s+)?(?:(?:bold|bolder|lighter|\d+)\s+)?(\S+)\s*/?\s*(?:\S+\s+)?(.+?)\s*(?:;|$)",
    re.IGNORECASE,
)


def _outlook_word_strip_unsupported(html: str) -> str:
    """Bulk-remove CSS properties unsupported by Word engine from inline styles."""

    def _strip(m: re.Match[str]) -> str:
        prefix = m.group(1)
        style = m.group(2)
        cleaned = _OUTLOOK_WORD_UNSUPPORTED_RE.sub("", style)
        cleaned = _SEMICOLON_CLEANUP_RE.sub(";", cleaned).strip("; ")
        return f'{prefix}{cleaned}"'

    return _INLINE_STYLE_RE.sub(_strip, html)


def _outlook_word_shorthand_expand(html: str) -> str:
    """Expand margin/padding shorthand and handle border/font shorthand."""

    def _expand_border(m: re.Match[str]) -> str:
        width, style, color = m.group(1), m.group(2), m.group(3)
        return f"border-width:{width};border-style:{style};border-color:{color};"

    def _rewrite(m: re.Match[str]) -> str:
        prefix = m.group(1)
        style = m.group(2)
        style = _SHORTHAND_MARGIN_RE.sub(lambda s: _expand_shorthand(s, "margin"), style)
        style = _SHORTHAND_PADDING_RE.sub(lambda s: _expand_shorthand(s, "padding"), style)
        style = _SHORTHAND_BORDER_RE.sub(_expand_border, style)
        style = _SHORTHAND_FONT_RE.sub("", style)  # Strip font shorthand
        return f'{prefix}{style}"'

    return _INLINE_STYLE_RE.sub(_rewrite, html)


def _outlook_word_max_width(html: str) -> str:
    """Inject width=600 on outermost <table>."""
    match = _TABLE_TAG_RE.search(html)
    if match:
        html = _TABLE_TAG_RE.sub(
            r'\1 width="600" style="width:100%;max-width:600px;"\2', html, count=1
        )
    return html


def _outlook_word_conditional_process(html: str) -> str:
    """Extract MSO conditional content, remove !mso blocks."""
    # Remove <!--[if !mso]><!-->...<![endif]--> blocks
    html = _NOT_MSO_CONDITIONAL_RE.sub("", html)
    # Unwrap <!--[if mso]>...<![endif]--> (keep inner HTML)
    html = _MSO_CONDITIONAL_RE.sub(r"\1", html)
    return html


def _outlook_word_vml_preserve(html: str) -> str:
    """No-op — VML elements pass through. Chromium won't render them in screenshots."""
    return html


# ── Thunderbird Emulator Rules ──

_THUNDERBIRD_UNSUPPORTED_CSS_RE = re.compile(
    r"position\s*:\s*sticky[^;]*;?|"
    r"backdrop-filter\s*:[^;]+;?|"
    r"clip-path\s*:[^;]+;?",
    re.IGNORECASE,
)


def _thunderbird_strip_unsupported(html: str) -> str:
    """Remove position: sticky, backdrop-filter, clip-path from inline styles."""

    def _strip(m: re.Match[str]) -> str:
        prefix = m.group(1)
        style = m.group(2)
        cleaned = _THUNDERBIRD_UNSUPPORTED_CSS_RE.sub("", style)
        cleaned = _SEMICOLON_CLEANUP_RE.sub(";", cleaned).strip("; ")
        return f'{prefix}{cleaned}"'

    return _INLINE_STYLE_RE.sub(_strip, html)


def _thunderbird_preserve_style_blocks(html: str) -> str:
    """No-op — Thunderbird respects <style> blocks."""
    return html


# ── Android Gmail Emulator Rules ──

_VIEWPORT_META_RE = re.compile(
    r'<meta\s+name\s*=\s*["\']viewport["\'][^>]*/?>',
    re.IGNORECASE,
)

_AMP_HTML_RE = re.compile(
    r"(<html\b[^>]*)\s*⚡4email([^>]*>)",
    re.IGNORECASE,
)


def _android_gmail_viewport_override(html: str) -> str:
    """Replace or inject viewport meta tag for mobile."""
    viewport = '<meta name="viewport" content="width=device-width, initial-scale=1">'
    if _VIEWPORT_META_RE.search(html):
        return _VIEWPORT_META_RE.sub(viewport, html)
    return _HEAD_TAG_RE.sub(r"\1" + viewport, html, count=1)


def _android_gmail_dark_mode(html: str) -> str:
    """Add data-ogsc and color-scheme:dark on <html> for system dark mode."""
    return _HTML_TAG_RE.sub(r'\1 data-ogsc style="color-scheme:dark;"\2', html, count=1)


def _android_gmail_amp_strip(html: str) -> str:
    """Strip ⚡4email from <html> tag."""
    return _AMP_HTML_RE.sub(r"\1\2", html)


# ── Emulator Registry ──

_GMAIL_WEB_RULES: list[EmulatorRule] = [
    EmulatorRule(name="strip_style_blocks", transform=_gmail_strip_style_blocks),
    EmulatorRule(name="strip_link_tags", transform=_gmail_strip_link_tags),
    EmulatorRule(name="rewrite_classes", transform=_gmail_rewrite_classes),
    EmulatorRule(
        name="strip_unsupported_inline_css", transform=_gmail_strip_unsupported_inline_css
    ),
    EmulatorRule(name="strip_form_elements", transform=_gmail_strip_form_elements),
    EmulatorRule(name="enforce_body_max_width", transform=_gmail_enforce_body_max_width),
]

_EMULATORS: dict[str, EmailClientEmulator] = {
    "gmail_web": EmailClientEmulator(
        client_id="gmail_web",
        rules=_GMAIL_WEB_RULES,
    ),
    "outlook_web": EmailClientEmulator(
        client_id="outlook_web",
        rules=[
            EmulatorRule(name="strip_unsupported_css", transform=_outlook_strip_unsupported_css),
            EmulatorRule(name="rewrite_shorthand", transform=_outlook_rewrite_shorthand),
            EmulatorRule(name="inject_dark_mode_attrs", transform=_outlook_inject_dark_mode_attrs),
        ],
    ),
    "yahoo_web": EmailClientEmulator(
        client_id="yahoo_web",
        rules=[
            EmulatorRule(name="strip_unsupported_css", transform=_yahoo_strip_unsupported_css),
            EmulatorRule(name="rewrite_classes", transform=_yahoo_rewrite_classes),
            EmulatorRule(name="enforce_max_width", transform=_yahoo_enforce_max_width),
        ],
    ),
    "yahoo_mobile": EmailClientEmulator(
        client_id="yahoo_mobile",
        rules=[
            EmulatorRule(name="strip_style_blocks", transform=_yahoo_strip_style_blocks),
            EmulatorRule(name="strip_unsupported_css", transform=_yahoo_strip_unsupported_css),
            EmulatorRule(name="rewrite_classes", transform=_yahoo_rewrite_classes),
            EmulatorRule(name="enforce_max_width", transform=_yahoo_enforce_max_width),
        ],
    ),
    "samsung_mail": EmailClientEmulator(
        client_id="samsung_mail",
        rules=[
            EmulatorRule(name="strip_unsupported_css", transform=_samsung_strip_unsupported_css),
            EmulatorRule(name="image_proxy", transform=_samsung_image_proxy),
            EmulatorRule(name="dark_mode_inject", transform=_samsung_dark_mode_inject),
        ],
    ),
    "outlook_desktop": EmailClientEmulator(
        client_id="outlook_desktop",
        rules=[
            EmulatorRule(name="word_strip_unsupported", transform=_outlook_word_strip_unsupported),
            EmulatorRule(name="word_shorthand_expand", transform=_outlook_word_shorthand_expand),
            EmulatorRule(name="word_max_width", transform=_outlook_word_max_width),
            EmulatorRule(
                name="word_conditional_process", transform=_outlook_word_conditional_process
            ),
            EmulatorRule(name="word_vml_preserve", transform=_outlook_word_vml_preserve),
        ],
    ),
    "thunderbird": EmailClientEmulator(
        client_id="thunderbird",
        rules=[
            EmulatorRule(name="strip_unsupported", transform=_thunderbird_strip_unsupported),
            EmulatorRule(
                name="preserve_style_blocks", transform=_thunderbird_preserve_style_blocks
            ),
        ],
    ),
    "android_gmail": EmailClientEmulator(
        client_id="android_gmail",
        rules=[
            *_GMAIL_WEB_RULES,
            EmulatorRule(name="viewport_override", transform=_android_gmail_viewport_override),
            EmulatorRule(name="dark_mode", transform=_android_gmail_dark_mode),
            EmulatorRule(name="amp_strip", transform=_android_gmail_amp_strip),
        ],
    ),
}


def get_emulator(client_id: str) -> EmailClientEmulator | None:
    """Get an emulator by client ID. Returns None if no emulator exists."""
    return _EMULATORS.get(client_id)
