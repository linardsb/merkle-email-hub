"""Extract design tokens from MJML ``<mj-head>``."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.design_sync.email_design_document import (
    DocumentColor,
    DocumentTokens,
    DocumentTypography,
)

if TYPE_CHECKING:
    from lxml import etree

# ── CSS regex helpers ────────────────────────────────────────────────

_CSS_VAR_RE = re.compile(r"--([a-zA-Z0-9_-]+)\s*:\s*(#[0-9a-fA-F]{3,8})")
_DARK_MODE_RE = re.compile(
    r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}",
    re.DOTALL,
)
_DARK_PROP_RE = re.compile(r"(background(?:-color)?|color)\s*:\s*(#[0-9a-fA-F]{3,8})")
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def _parse_float(value: str | None, default: float = 0.0) -> float:
    if not value:
        return default
    try:
        return float(value.replace("px", "").replace("em", "").replace("rem", "").strip())
    except ValueError:
        return default


def _is_hex(value: str | None) -> bool:
    return bool(value and _HEX_RE.match(value))


# ── Public API ───────────────────────────────────────────────────────


def extract_tokens(head: etree._Element | None) -> DocumentTokens:
    """Extract design tokens from ``<mj-head>``.

    Returns empty ``DocumentTokens`` when *head* is ``None``.
    """
    if head is None:
        return DocumentTokens()

    typography: list[DocumentTypography] = []
    colors: list[DocumentColor] = []
    dark_colors: list[DocumentColor] = []
    seen_hex: set[str] = set()

    # ── <mj-attributes> ─────────────────────────────────────────────
    attrs_el = head.find("mj-attributes")
    if attrs_el is not None:
        for child in attrs_el:
            tag = _local_tag(child)
            if tag in ("mj-all", "mj-text", "mj-button"):
                typo = _typography_from_attrs(child, name=tag.replace("mj-", ""))
                if typo is not None:
                    typography.append(typo)
                color_val = child.get("color")
                if _is_hex(color_val):
                    _add_color(colors, seen_hex, f"{tag}-color", color_val)  # type: ignore[arg-type]
                bg = child.get("background-color")
                if _is_hex(bg):
                    _add_color(colors, seen_hex, f"{tag}-bg", bg)  # type: ignore[arg-type]

    # ── <mj-style> CSS blocks ────────────────────────────────────────
    for style_el in head.findall("mj-style"):
        css_text = (style_el.text or "").strip()
        if not css_text:
            continue

        # CSS custom-property colours
        for match in _CSS_VAR_RE.finditer(css_text):
            _add_color(colors, seen_hex, match.group(1), match.group(2))

        # Dark mode colours
        for dm_match in _DARK_MODE_RE.finditer(css_text):
            block = dm_match.group(1)
            for prop_match in _DARK_PROP_RE.finditer(block):
                prop_name = prop_match.group(1)
                hex_val = prop_match.group(2)
                dark_colors.append(DocumentColor(name=f"dark-{prop_name}", hex=hex_val))

    # ── <mj-font> web font references ────────────────────────────────
    for font_el in head.findall("mj-font"):
        name = font_el.get("name")
        if name:
            typography.append(
                DocumentTypography(
                    name=f"font-{name}",
                    family=name,
                    weight="400",
                    size=16.0,
                    line_height=1.5,
                )
            )

    return DocumentTokens(
        colors=colors,
        typography=typography,
        dark_colors=dark_colors,
    )


# ── Private helpers ──────────────────────────────────────────────────


def _local_tag(el: etree._Element) -> str:
    tag = el.tag
    if isinstance(tag, str) and "}" in tag:
        return tag.split("}", 1)[1]
    return str(tag)


def _add_color(
    colors: list[DocumentColor],
    seen: set[str],
    name: str,
    hex_val: str,
) -> None:
    key = hex_val.lower()
    if key not in seen:
        seen.add(key)
        colors.append(DocumentColor(name=name, hex=hex_val))


def _typography_from_attrs(
    el: etree._Element,
    name: str,
) -> DocumentTypography | None:
    family = el.get("font-family")
    size = el.get("font-size")
    weight = el.get("font-weight")
    # Need at least font-family or font-size to create a meaningful entry
    if not family and not size:
        return None
    return DocumentTypography(
        name=name,
        family=family or "inherit",
        weight=weight or "400",
        size=_parse_float(size, 16.0),
        line_height=_parse_float(el.get("line-height"), 1.5),
        letter_spacing=_parse_float(el.get("letter-spacing")) or None,
    )
