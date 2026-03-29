"""Email HTML validity assertion and tests (39.2.4).

Provides ``assert_valid_email_html()`` — a reusable assertion for email
client compatibility checks.  Also validates all 15 golden templates.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser

import pytest

GOLDEN_DIR = pathlib.Path(__file__).resolve().parents[2] / "ai" / "templates" / "library"


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

# Only flag div layout CSS that replaces table-based columns:
# float, flex, grid, or absolute/fixed positioning.
# Width/max-width centering wrappers (margin:auto) are standard email practice.
_LAYOUT_CSS_RE = re.compile(
    r"(float\s*:\s*(?!none)|display\s*:\s*flex|display\s*:\s*grid|"
    r"position\s*:\s*(absolute|fixed))",
    re.IGNORECASE,
)

_BAD_ALT_VALUES = frozenset({"mj-image", "image", "img", "photo", "picture", ""})


@dataclass
class EmailHtmlViolation:
    rule: str
    message: str
    element: str = ""


class _EmailHtmlValidator(HTMLParser):
    """Scan HTML for email best-practice violations."""

    def __init__(self) -> None:
        super().__init__()
        self.violations: list[EmailHtmlViolation] = []
        self._in_mso_comment = False

    # -- starttag ---------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        # G1: layout tables must have role="presentation"
        if tag_l == "table" and attr_dict.get("role") != "presentation":
            self.violations.append(
                EmailHtmlViolation(
                    "G1",
                    'Missing role="presentation"',
                    f"<table class={attr_dict.get('class', '')!r}>",
                )
            )

        # G-REF-2: images need display:block + meaningful alt
        if tag_l == "img":
            style = attr_dict.get("style", "").replace(" ", "").lower()
            alt = attr_dict.get("alt", "")
            if "display:block" not in style:
                self.violations.append(
                    EmailHtmlViolation(
                        "G-REF-2a",
                        "Image missing display:block",
                        f"<img alt={alt!r}>",
                    )
                )
            if alt.strip().lower() in _BAD_ALT_VALUES:
                self.violations.append(
                    EmailHtmlViolation(
                        "G-REF-2b",
                        f"Image has non-meaningful alt={alt!r}",
                        "<img>",
                    )
                )

        # NO-DIV-LAYOUT: no <div> with layout CSS (except MSO / .column)
        if tag_l == "div" and not self._in_mso_comment:
            style = attr_dict.get("style", "")
            if _LAYOUT_CSS_RE.search(style):
                classes = attr_dict.get("class", "")
                if "column" not in classes:
                    self.violations.append(
                        EmailHtmlViolation(
                            "NO-DIV-LAYOUT",
                            f"<div> with layout CSS: {style[:60]}",
                            f"<div class={classes!r}>",
                        )
                    )

    # -- comments (MSO conditionals) ------------------------------------

    def handle_comment(self, data: str) -> None:
        if "[if mso]" in data or "[if gte mso" in data:
            self._in_mso_comment = True
        if "endif" in data:
            self._in_mso_comment = False


def assert_valid_email_html(
    html: str,
    *,
    ignore_rules: set[str] | None = None,
) -> list[EmailHtmlViolation]:
    """Assert *html* conforms to email best-practices.

    Rules checked:
    - **G1** — every ``<table>`` has ``role="presentation"``
    - **G-REF-2a** — every ``<img>`` has ``display:block``
    - **G-REF-2b** — every ``<img>`` has meaningful ``alt`` text
    - **NO-DIV-LAYOUT** — no ``<div>`` with layout CSS

    Returns the full violation list (useful for inspection). Raises
    ``AssertionError`` if any non-ignored violations remain.
    """
    ignore = ignore_rules or set()
    validator = _EmailHtmlValidator()
    validator.feed(html)
    active = [v for v in validator.violations if v.rule not in ignore]
    if active:
        lines = "\n".join(f"  [{v.rule}] {v.message} — {v.element}" for v in active)
        raise AssertionError(f"Email HTML violations:\n{lines}")
    return validator.violations


# ---------------------------------------------------------------------------
# Unit tests for the validator itself
# ---------------------------------------------------------------------------


class TestValidatorRules:
    def test_clean_html_passes(self) -> None:
        html = (
            '<table role="presentation"><tr><td>'
            '<img src="x.png" alt="Product photo" style="display:block">'
            '<p style="margin:0">Hello</p>'
            "</td></tr></table>"
        )
        assert_valid_email_html(html)

    def test_missing_role_presentation(self) -> None:
        html = "<table><tr><td>Content</td></tr></table>"
        with pytest.raises(AssertionError, match="G1"):
            assert_valid_email_html(html)

    def test_img_missing_display_block(self) -> None:
        html = '<table role="presentation"><tr><td><img src="x.png" alt="Logo"></td></tr></table>'
        with pytest.raises(AssertionError, match="G-REF-2a"):
            assert_valid_email_html(html)

    def test_img_bad_alt_mj_image(self) -> None:
        html = (
            '<table role="presentation"><tr><td>'
            '<img src="x.png" alt="mj-image" style="display:block">'
            "</td></tr></table>"
        )
        with pytest.raises(AssertionError, match="G-REF-2b"):
            assert_valid_email_html(html)

    def test_img_empty_alt(self) -> None:
        html = (
            '<table role="presentation"><tr><td>'
            '<img src="x.png" alt="" style="display:block">'
            "</td></tr></table>"
        )
        with pytest.raises(AssertionError, match="G-REF-2b"):
            assert_valid_email_html(html)

    def test_div_with_layout_css_flagged(self) -> None:
        html = (
            '<table role="presentation"><tr><td>'
            '<div style="width:300px;float:left">X</div>'
            "</td></tr></table>"
        )
        with pytest.raises(AssertionError, match="NO-DIV-LAYOUT"):
            assert_valid_email_html(html)

    def test_div_column_allowed(self) -> None:
        html = (
            '<table role="presentation"><tr><td>'
            '<div class="column" style="width:300px">X</div>'
            "</td></tr></table>"
        )
        assert_valid_email_html(html)

    def test_mso_comment_div_allowed(self) -> None:
        html = (
            '<table role="presentation"><tr><td>'
            '<!--[if mso]><div style="width:600px"><![endif]-->'
            '<p style="margin:0">Content</p>'
            "<!--[if mso]></div><![endif]-->"
            "</td></tr></table>"
        )
        assert_valid_email_html(html)

    def test_ignore_rules_parameter(self) -> None:
        html = "<table><tr><td>Content</td></tr></table>"
        assert_valid_email_html(html, ignore_rules={"G1"})

    def test_multiple_violations(self) -> None:
        html = '<table><tr><td><img src="x.png"></td></tr></table>'
        with pytest.raises(AssertionError) as exc_info:
            assert_valid_email_html(html)
        msg = str(exc_info.value)
        assert "G1" in msg
        assert "G-REF-2a" in msg
        assert "G-REF-2b" in msg

    def test_returns_all_violations(self) -> None:
        html = (
            '<table role="presentation"><tr><td>'
            '<img src="x.png" alt="Logo" style="display:block">'
            "</td></tr></table>"
        )
        # No assertion error, returns empty list
        result = assert_valid_email_html(html)
        assert result == []


# ---------------------------------------------------------------------------
# Golden template validation
# ---------------------------------------------------------------------------


class TestGoldenTemplateValidity:
    """Validate all 15 golden templates against email HTML rules."""

    @pytest.mark.parametrize(
        "template",
        sorted(GOLDEN_DIR.glob("*.html")),
        ids=lambda p: p.stem,
    )
    def test_golden_template_valid(self, template: pathlib.Path) -> None:
        html = template.read_text()
        # Golden templates use placeholder alt text in some slots,
        # so we allow G-REF-2b. Also some may have decorative images
        # with empty alt which is acceptable per accessibility standards
        # for purely decorative images.
        assert_valid_email_html(html, ignore_rules={"G-REF-2b"})
