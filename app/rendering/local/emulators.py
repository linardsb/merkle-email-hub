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


def _gmail_strip_style_blocks(html: str) -> str:
    """Remove all <style> tags (Gmail strips embedded CSS)."""
    return _STYLE_TAG_RE.sub("", html)


def _gmail_strip_link_tags(html: str) -> str:
    """Remove <link rel="stylesheet"> tags."""
    return _LINK_TAG_RE.sub("", html)


def _gmail_rewrite_classes(html: str) -> str:
    """Prefix class names with random ID (Gmail behavior: .foo -> .m_123_foo)."""
    prefix = "m_" + hashlib.md5(html[:200].encode()).hexdigest()[:6] + "_"

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
        cleaned = re.sub(r";\s*;+", ";", cleaned).strip("; ")
        return f'{prefix}{cleaned}"'

    return _INLINE_STYLE_RE.sub(_strip, html)


def _gmail_strip_form_elements(html: str) -> str:
    """Remove <form>, <input>, <button>, <select>, <svg>, <math> elements."""
    return _FORM_ELEMENTS_RE.sub("", html)


def _gmail_enforce_body_max_width(html: str) -> str:
    """Inject max-width: 680px on body."""
    body_re = re.compile(r"(<body\b[^>]*)(>)", re.IGNORECASE)
    match = body_re.search(html)
    if match:
        tag = match.group(1)
        if 'style="' in tag.lower():
            # Append to existing style
            html = body_re.sub(
                lambda m: re.sub(
                    r'(style\s*=\s*")',
                    r'\1max-width:680px;margin:0 auto;',
                    m.group(1),
                    flags=re.IGNORECASE,
                )
                + m.group(2),
                html,
                count=1,
            )
        else:
            html = body_re.sub(
                r'\1 style="max-width:680px;margin:0 auto;"\2', html, count=1
            )
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
        cleaned = re.sub(r";\s*;+", ";", cleaned).strip("; ")
        return f'{prefix}{cleaned}"'

    return _INLINE_STYLE_RE.sub(_strip, html)


def _expand_shorthand(match: re.Match[str], prop: str) -> str:
    """Expand margin/padding shorthand to longhand."""
    top = match.group(1)
    right = match.group(2) or top
    bottom = match.group(3) or top
    left = match.group(4) or right
    return (
        f"{prop}-top:{top};{prop}-right:{right};"
        f"{prop}-bottom:{bottom};{prop}-left:{left};"
    )


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
    body_re = re.compile(r"(<body\b[^>]*)(>)", re.IGNORECASE)
    match = body_re.search(html)
    if match:
        html = body_re.sub(r'\1 data-ogsc data-ogsb\2', html, count=1)
    return html


# ── Emulator Registry ──

_EMULATORS: dict[str, EmailClientEmulator] = {
    "gmail_web": EmailClientEmulator(
        client_id="gmail_web",
        rules=[
            EmulatorRule(name="strip_style_blocks", transform=_gmail_strip_style_blocks),
            EmulatorRule(name="strip_link_tags", transform=_gmail_strip_link_tags),
            EmulatorRule(name="rewrite_classes", transform=_gmail_rewrite_classes),
            EmulatorRule(name="strip_unsupported_inline_css", transform=_gmail_strip_unsupported_inline_css),
            EmulatorRule(name="strip_form_elements", transform=_gmail_strip_form_elements),
            EmulatorRule(name="enforce_body_max_width", transform=_gmail_enforce_body_max_width),
        ],
    ),
    "outlook_web": EmailClientEmulator(
        client_id="outlook_web",
        rules=[
            EmulatorRule(name="strip_unsupported_css", transform=_outlook_strip_unsupported_css),
            EmulatorRule(name="rewrite_shorthand", transform=_outlook_rewrite_shorthand),
            EmulatorRule(name="inject_dark_mode_attrs", transform=_outlook_inject_dark_mode_attrs),
        ],
    ),
}


def get_emulator(client_id: str) -> EmailClientEmulator | None:
    """Get an emulator by client ID. Returns None if no emulator exists."""
    return _EMULATORS.get(client_id)
