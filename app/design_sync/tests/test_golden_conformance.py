"""Golden template conformance gate — CI-mandatory.

Validates converter output against patterns from email-templates/components/.
Runs as part of ``make golden-conformance`` and ``make check``.

Checks are regex-based and divided into:
- Universal checks (run on all fragment converter output)
- Shell checks (validate raw email-shell.html golden patterns)
- Component-specific checks (column class, MSO conditionals, VML)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from app.design_sync.converter_service import DesignConverterService
from app.design_sync.html_import.adapter import HtmlImportAdapter

_COMPONENTS_DIR = Path(__file__).resolve().parents[3] / "email-templates" / "components"

# Fragment components: go through import → convert round-trip
_FRAGMENT_COMPONENTS = [
    "hero-block.html",
    "column-layout-2.html",
    "column-layout-3.html",
    "column-layout-4.html",
    "full-width-image.html",
    "cta-button.html",
    "product-card.html",
    "image-grid.html",
    "article-card.html",
    "header.html",
    "footer.html",
    "logo-header.html",
    "navigation-bar.html",
    "preheader.html",
    "reverse-column.html",
]

_SHELL_COMPONENT = "email-shell.html"


# ── Check definitions ────────────────────────────────────────────


@dataclass(frozen=True)
class ConformanceCheck:
    id: str
    pattern: str  # regex
    should_match: bool  # True = must find, False = must NOT find
    description: str
    scope: str = "all"  # "all" | "fragment" | "shell"


# Universal checks applied to every fragment's converter output.
# G2 is "positive-if-present" — only enforced when <img> tags exist.
# G5 (no div layout CSS) is tested separately in test_no_bare_div_layout
# because it requires stripping MSO conditionals and class="column" divs first.
CHECKS: list[ConformanceCheck] = [
    ConformanceCheck(
        "G1",
        r'<table\b[^>]*\brole="presentation"',
        True,
        "Layout tables must have role='presentation'",
    ),
    ConformanceCheck(
        "G3-neg",
        r'\balt="(|image|photo|picture|img|mj-image|mj-text|frame|banner)"',
        False,
        "Images must not have generic/empty alt text",
    ),
    ConformanceCheck(
        "G7",
        r'<table\b[^>]*cellpadding="0"[^>]*cellspacing="0"',
        True,
        "Tables must have cellpadding=0 cellspacing=0",
    ),
    ConformanceCheck(
        "G11",
        r"mso-table-lspace:\s*0p?t",
        True,
        "Tables should have MSO table space reset",
    ),
    ConformanceCheck(
        "G-NO-P-H",
        r"<(p|h[1-6])[\s>]",
        False,
        "No <p> or <h1>-<h6> tags in output — all text in <td>",
    ),
]


# ── Helpers ──────────────────────────────────────────────────────


def _load(name: str) -> str:
    return (_COMPONENTS_DIR / name).read_text()


def _wrap(fragment: str, width: int = 600) -> str:
    return (
        f'<html><body><div style="max-width:{width}px">'
        f'<table width="{width}" align="center" role="presentation" '
        f'cellpadding="0" cellspacing="0" style="width:{width}px;">'
        f"<tr><td>{fragment}</td></tr></table></div></body></html>"
    )


async def _import_and_convert(html: str) -> str:
    adapter = HtmlImportAdapter()
    with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
        doc = await adapter.parse(html, use_ai=False)
    svc = DesignConverterService()
    return svc.convert_document(doc).html


def _check_html(html: str, check: ConformanceCheck) -> str | None:
    """Return violation message or None if check passes."""
    found = bool(re.search(check.pattern, html, re.IGNORECASE))
    if check.should_match and not found:
        return f"[{check.id}] MISSING: {check.description}"
    if not check.should_match and found:
        return f"[{check.id}] VIOLATION: {check.description}"
    return None


def _strip_mso_and_column_divs(html: str) -> str:
    """Remove MSO conditional blocks and class='column' divs for G5 check."""
    stripped = re.sub(r"<!--\[if mso\]>.*?<!\[endif\]-->", "", html, flags=re.DOTALL)
    return re.sub(r'<div[^>]*class="column"[^>]*>', "", stripped)


# ── Tests ────────────────────────────────────────────────────────


class TestGoldenConformance:
    """CI gate: converter output must conform to golden component patterns."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("component", _FRAGMENT_COMPONENTS)
    async def test_fragment_conformance(self, component: str) -> None:
        raw = _load(component)
        html = await _import_and_convert(_wrap(raw))
        violations: list[str] = []
        for check in CHECKS:
            if check.scope in ("all", "fragment"):
                msg = _check_html(html, check)
                if msg:
                    violations.append(msg)
        assert not violations, f"Conformance failures for {component}:\n" + "\n".join(
            f"  - {v}" for v in violations
        )

    @pytest.mark.asyncio
    async def test_shell_conformance(self) -> None:
        """email-shell.html: validate full-document patterns."""
        raw = _load(_SHELL_COMPONENT)
        checks = [
            ConformanceCheck(
                "G10a",
                r"x-apple-disable-message-reformatting",
                True,
                "Shell must have Apple reformatting meta",
            ),
            ConformanceCheck(
                "G10b",
                r"format-detection",
                True,
                "Shell must have format-detection meta",
            ),
            ConformanceCheck(
                "G10c",
                r"color-scheme.*light\s+dark",
                True,
                "Shell must declare light dark color-scheme",
            ),
            ConformanceCheck(
                "G6",
                r"<!--\[if mso\]>",
                True,
                "Shell must have MSO conditionals",
            ),
        ]
        violations: list[str] = []
        for check in checks:
            msg = _check_html(raw, check)
            if msg:
                violations.append(msg)
        assert not violations, "Shell conformance failures:\n" + "\n".join(
            f"  - {v}" for v in violations
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("component", _FRAGMENT_COMPONENTS)
    async def test_images_have_display_block(self, component: str) -> None:
        """G2: Every <img> must have display:block (skipped if no images)."""
        raw = _load(component)
        html = await _import_and_convert(_wrap(raw))
        if not re.search(r"<img\b", html):
            pytest.skip(f"{component}: no <img> tags in output")
        assert re.search(r"<img\b[^>]*display:\s*block", html, re.IGNORECASE), (
            f"{component}: <img> without display:block"
        )

    @pytest.mark.asyncio
    async def test_column_layout_has_column_class(self) -> None:
        """Column layouts must produce div.column wrappers."""
        for comp in (
            "column-layout-2.html",
            "column-layout-3.html",
            "column-layout-4.html",
        ):
            raw = _load(comp)
            html = await _import_and_convert(_wrap(raw))
            assert re.search(r'class="column"', html), (
                f"{comp}: converter output missing div.column wrapper"
            )

    @pytest.mark.asyncio
    async def test_mso_conditionals_present(self) -> None:
        """Column layouts must include MSO ghost tables."""
        for comp in (
            "column-layout-2.html",
            "image-grid.html",
            "reverse-column.html",
        ):
            raw = _load(comp)
            html = await _import_and_convert(_wrap(raw))
            assert re.search(r"<!--\[if mso\]>", html), (
                f"{comp}: converter output missing MSO conditionals"
            )

    @pytest.mark.asyncio
    async def test_cta_button_has_vml(self) -> None:
        """CTA button should have VML fallback for Outlook."""
        raw = _load("cta-button.html")
        html = await _import_and_convert(_wrap(raw))
        assert re.search(r"v:roundrect|<!--\[if mso\]>", html), (
            "cta-button.html: converter output missing VML/MSO fallback"
        )

    @pytest.mark.asyncio
    async def test_no_bare_div_layout(self) -> None:
        """No component output should use div for layout (width/flex/float)."""
        for comp in _FRAGMENT_COMPONENTS:
            raw = _load(comp)
            html = await _import_and_convert(_wrap(raw))
            stripped = _strip_mso_and_column_divs(html)
            match = re.search(r'<div\b[^>]*style="[^"]*\b(width|flex|float)\s*:', stripped)
            assert not match, f"{comp}: div with layout CSS found: {match.group(0)}"
