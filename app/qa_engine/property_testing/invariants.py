# pyright: reportUnnecessaryIsInstance=false
"""Email invariants — properties that must hold regardless of content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from lxml import html as lxml_html
from lxml.html import HtmlElement


@dataclass(frozen=True)
class InvariantResult:
    """Result of checking a single invariant."""

    invariant_name: str
    passed: bool
    violations: tuple[str, ...] = ()


class EmailInvariant(Protocol):
    """Protocol for email invariants."""

    name: str

    def check(self, html: str) -> InvariantResult: ...


def _parse_html(html: str) -> HtmlElement:
    """Parse HTML string into lxml element."""
    doc: HtmlElement = lxml_html.fromstring(html)
    return doc


class SizeLimit:
    """Gmail 102KB clipping threshold."""

    name = "size_limit"

    def check(self, html: str) -> InvariantResult:
        size = len(html.encode("utf-8"))
        if size > 102_400:
            return InvariantResult(
                invariant_name=self.name,
                passed=False,
                violations=(
                    f"HTML size {size:,} bytes exceeds 102,400 byte Gmail clipping threshold",
                ),
            )
        return InvariantResult(invariant_name=self.name, passed=True)


class ImageWidth:
    """All images must be ≤ 600px wide."""

    name = "image_width"

    def check(self, html: str) -> InvariantResult:
        doc = _parse_html(html)
        violations: list[str] = []
        for i, img in enumerate(doc.iter("img")):
            src = img.get("src", f"image[{i}]")
            # Check width attribute
            width_attr = img.get("width")
            if width_attr:
                try:
                    w = int(width_attr.replace("px", ""))
                    if w > 600:
                        violations.append(f"Image '{src}' has width={w}px (max 600)")
                except ValueError:
                    pass
            # Check inline style width
            style = img.get("style", "")
            match = re.search(r"width\s*:\s*(\d+)px", style)
            if match and int(match.group(1)) > 600:
                violations.append(
                    f"Image '{src}' has inline style width={match.group(1)}px (max 600)"
                )
        if violations:
            return InvariantResult(
                invariant_name=self.name, passed=False, violations=tuple(violations)
            )
        return InvariantResult(invariant_name=self.name, passed=True)


class LinkIntegrity:
    """Every <a> must have a non-empty, non-javascript href."""

    name = "link_integrity"

    def check(self, html: str) -> InvariantResult:
        doc = _parse_html(html)
        violations: list[str] = []
        for i, a in enumerate(doc.iter("a")):
            href = a.get("href")
            if href is None or href.strip() == "":
                text = (a.text or "").strip()[:30]
                violations.append(f"Link[{i}] '{text}' has empty href")
            elif href.strip().lower().startswith("javascript:"):
                violations.append(f"Link[{i}] has javascript: URI")
        if violations:
            return InvariantResult(
                invariant_name=self.name, passed=False, violations=tuple(violations)
            )
        return InvariantResult(invariant_name=self.name, passed=True)


class AltTextPresence:
    """Every <img> must have non-empty alt (except tracking pixels)."""

    name = "alt_text"

    def check(self, html: str) -> InvariantResult:
        doc = _parse_html(html)
        violations: list[str] = []
        for i, img in enumerate(doc.iter("img")):
            # Skip tracking pixels (1x1)
            w = img.get("width", "")
            h = img.get("height", "")
            if w in ("1", "0") and h in ("1", "0"):
                continue
            alt = img.get("alt")
            if alt is None or alt.strip() == "":
                src = img.get("src", f"image[{i}]")
                violations.append(f"Image '{src}' missing alt text")
        if violations:
            return InvariantResult(
                invariant_name=self.name, passed=False, violations=tuple(violations)
            )
        return InvariantResult(invariant_name=self.name, passed=True)


class TableNestingDepth:
    """Table nesting must not exceed 8 levels (Outlook rendering limit)."""

    name = "table_nesting"

    def check(self, html: str) -> InvariantResult:
        doc = _parse_html(html)
        max_depth = self._max_table_depth(doc, 0)
        if max_depth > 8:
            return InvariantResult(
                invariant_name=self.name,
                passed=False,
                violations=(f"Table nesting depth {max_depth} exceeds maximum of 8",),
            )
        return InvariantResult(invariant_name=self.name, passed=True)

    def _max_table_depth(self, element: HtmlElement, current: int) -> int:
        """Recursively find maximum table nesting depth."""
        depth = current
        for child in element:
            if not isinstance(child, HtmlElement):
                continue
            child_depth = current + 1 if child.tag == "table" else current
            depth = max(depth, self._max_table_depth(child, child_depth))
        return depth


class EncodingValid:
    """HTML must be valid UTF-8 with no null bytes."""

    name = "encoding_valid"

    def check(self, html: str) -> InvariantResult:
        violations: list[str] = []
        if "\x00" in html:
            violations.append("HTML contains null bytes")
        try:
            html.encode("utf-8")
        except UnicodeEncodeError as e:
            violations.append(f"Invalid UTF-8 encoding: {e}")
        if violations:
            return InvariantResult(
                invariant_name=self.name, passed=False, violations=tuple(violations)
            )
        return InvariantResult(invariant_name=self.name, passed=True)


class MSOBalance:
    """MSO conditional comments must be balanced."""

    name = "mso_balance"

    _OPEN_PATTERN = re.compile(r"<!--\[if\s+[^\]]*\]>")
    _CLOSE_PATTERN = re.compile(r"<!\[endif\]-->")

    def check(self, html: str) -> InvariantResult:
        opens = len(self._OPEN_PATTERN.findall(html))
        closes = len(self._CLOSE_PATTERN.findall(html))
        if opens == 0 and closes == 0:
            return InvariantResult(invariant_name=self.name, passed=True)
        if opens != closes:
            return InvariantResult(
                invariant_name=self.name,
                passed=False,
                violations=(f"Unbalanced MSO conditionals: {opens} opening vs {closes} closing",),
            )
        return InvariantResult(invariant_name=self.name, passed=True)


class DarkModeReady:
    """If prefers-color-scheme is used, color-scheme meta must be present."""

    name = "dark_mode_ready"

    def check(self, html: str) -> InvariantResult:
        has_prefers = "prefers-color-scheme" in html
        if not has_prefers:
            return InvariantResult(invariant_name=self.name, passed=True)
        # Check for color-scheme meta tag
        has_meta = bool(re.search(r'<meta\s+name="color-scheme"', html))
        if not has_meta:
            return InvariantResult(
                invariant_name=self.name,
                passed=False,
                violations=(
                    'Uses prefers-color-scheme but missing <meta name="color-scheme"> tag',
                ),
            )
        return InvariantResult(invariant_name=self.name, passed=True)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int] | None:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        return None
    try:
        return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
    except ValueError:
        return None


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.0."""

    def linearize(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(lum1: float, lum2: float) -> float:
    """Calculate contrast ratio between two luminance values."""
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


class ContrastRatio:
    """Inline color/background-color pairs must meet WCAG 4.5:1."""

    name = "contrast_ratio"

    _COLOR_RE = re.compile(r"(?:^|;)\s*color\s*:\s*(#[0-9a-fA-F]{3,6})")
    _BG_RE = re.compile(r"background-color\s*:\s*(#[0-9a-fA-F]{3,6})")

    def check(self, html: str) -> InvariantResult:
        doc = _parse_html(html)
        violations: list[str] = []
        for element in doc.iter():
            if not isinstance(element, HtmlElement):
                continue
            style = element.get("style", "")
            if not style:
                continue
            color_match = self._COLOR_RE.search(style)
            bg_match = self._BG_RE.search(style)
            if color_match and bg_match:
                fg_rgb = _hex_to_rgb(color_match.group(1))
                bg_rgb = _hex_to_rgb(bg_match.group(1))
                if fg_rgb and bg_rgb:
                    fg_lum = _relative_luminance(*fg_rgb)
                    bg_lum = _relative_luminance(*bg_rgb)
                    ratio = _contrast_ratio(fg_lum, bg_lum)
                    if ratio < 4.5:
                        tag = str(element.tag)
                        violations.append(
                            f"<{tag}> has contrast ratio {ratio:.2f}:1 "
                            f"({color_match.group(1)} on {bg_match.group(1)}, "
                            f"minimum 4.5:1)"
                        )
        if violations:
            return InvariantResult(
                invariant_name=self.name, passed=False, violations=tuple(violations)
            )
        return InvariantResult(invariant_name=self.name, passed=True)


class ViewportFit:
    """No element should have explicit width > 600px."""

    name = "viewport_fit"

    _INLINE_WIDTH_RE = re.compile(r"width\s*:\s*(\d+)px")

    def check(self, html: str) -> InvariantResult:
        doc = _parse_html(html)
        violations: list[str] = []
        for element in doc.iter():
            if not isinstance(element, HtmlElement):
                continue
            tag = str(element.tag)
            # Check width attribute (tables, images)
            width_attr = element.get("width")
            if width_attr:
                try:
                    w = int(width_attr.replace("px", ""))
                    if w > 600:
                        violations.append(f"<{tag}> has width={w}px (max 600)")
                except ValueError:
                    pass
            # Check inline style width
            style = element.get("style", "")
            match = self._INLINE_WIDTH_RE.search(style)
            if match and int(match.group(1)) > 600:
                violations.append(f"<{tag}> has inline style width={match.group(1)}px (max 600)")
        if violations:
            return InvariantResult(
                invariant_name=self.name, passed=False, violations=tuple(violations)
            )
        return InvariantResult(invariant_name=self.name, passed=True)


_ALL_INVARIANT_INSTANCES: list[EmailInvariant] = [
    SizeLimit(),
    ImageWidth(),
    LinkIntegrity(),
    AltTextPresence(),
    TableNestingDepth(),
    EncodingValid(),
    MSOBalance(),
    DarkModeReady(),
    ContrastRatio(),
    ViewportFit(),
]

ALL_INVARIANTS: dict[str, EmailInvariant] = {inv.name: inv for inv in _ALL_INVARIANT_INSTANCES}
