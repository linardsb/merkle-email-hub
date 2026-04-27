# ruff: noqa: ARG001
"""CSS syntax validation custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

import logging as _stdlib_logging
import re

import cssutils
from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import register_custom_check

# Silence cssutils logging (it logs parse errors to stderr by default)
cssutils.log.setLevel(_stdlib_logging.CRITICAL)  # pyright: ignore[reportUnknownMemberType,reportArgumentType]


# ---------------------------------------------------------------------------
# CSS Syntax Validation check functions
# ---------------------------------------------------------------------------


_VENDOR_PREFIX_RE = re.compile(r"-(?:webkit|moz|ms|o)-[\w-]+")
_IMPORTANT_RE = re.compile(r"!important", re.IGNORECASE)
_IMPORT_RE = re.compile(r"@import\s", re.IGNORECASE)
_STYLE_BLOCK_RE_CSS = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
_INLINE_STYLE_RE_CSS = re.compile(r"style\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", re.IGNORECASE)
_LINK_STYLESHEET_RE = re.compile(r"<link[^>]+rel\s*=\s*[\"']stylesheet[\"'][^>]*>", re.IGNORECASE)
_EMPTY_DECL_RE = re.compile(r"([\w-]+)\s*:\s*;")
# Layout-critical properties that MUST be inlined for Gmail
_LAYOUT_CRITICAL_PROPS = frozenset(
    {
        "display",
        "width",
        "max-width",
        "min-width",
        "height",
        "float",
        "position",
        "margin",
        "padding",
        "text-align",
        "vertical-align",
        "background-color",
        "color",
        "font-size",
        "font-family",
        "line-height",
        "border",
    }
)


def _css_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve a CSS syntax check parameter from config."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def _parse_css_blocks(html: str) -> list[str]:
    """Extract CSS content from <style> blocks."""
    return [m.group(1) for m in _STYLE_BLOCK_RE_CSS.finditer(html)]


def _parse_inline_styles(html: str) -> list[str]:
    """Extract inline style values from both double- and single-quoted attributes."""
    return [m.group(1) or m.group(2) for m in _INLINE_STYLE_RE_CSS.finditer(html)]


def css_syntax_errors(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect CSS syntax errors using cssutils parser."""
    blocks = _parse_css_blocks(raw_html)
    if not blocks:
        return [], 0.0

    max_reported = int(_css_param(config, "max_syntax_errors_reported", 5))
    deduction = _css_param(config, "deduction_syntax_error", 0.15)

    all_errors: list[str] = []
    for block in blocks:
        sheet = cssutils.parseString(block, validate=True)  # pyright: ignore[reportUnknownMemberType]  # type: ignore[no-untyped-call]
        for rule in sheet:
            if rule.type == rule.UNKNOWN_RULE:
                all_errors.append(f"Unknown CSS rule: {rule.cssText[:60]}")

    if not all_errors:
        return [], 0.0

    issues = all_errors[:max_reported]
    if len(all_errors) > max_reported:
        issues.append(f"... and {len(all_errors) - max_reported} more syntax errors")

    return issues, deduction


def css_empty_declarations(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect empty CSS declarations (property: ;)."""
    max_reported = int(_css_param(config, "max_empty_declarations_reported", 5))
    deduction = _css_param(config, "deduction_empty_declaration", 0.05)

    all_css = _parse_css_blocks(raw_html) + _parse_inline_styles(raw_html)
    issues: list[str] = []

    for css in all_css:
        for m in _EMPTY_DECL_RE.finditer(css):
            issues.append(f"Empty declaration: '{m.group(1)}: ;'")

    if not issues:
        return [], 0.0

    reported = issues[:max_reported]
    if len(issues) > max_reported:
        reported.append(f"... and {len(issues) - max_reported} more")

    return reported, deduction


def css_vendor_prefixes(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect vendor-prefixed CSS properties (useless in email)."""
    max_reported = int(_css_param(config, "max_vendor_prefixes_reported", 5))
    deduction = _css_param(config, "deduction_vendor_prefix", 0.05)

    all_css = "\n".join(_parse_css_blocks(raw_html) + _parse_inline_styles(raw_html))
    matches = _VENDOR_PREFIX_RE.findall(all_css)

    if not matches:
        return [], 0.0

    unique = sorted(set(matches))
    issues = [f"Vendor prefix: '{p}' (ignored by email clients)" for p in unique[:max_reported]]
    if len(unique) > max_reported:
        issues.append(f"... and {len(unique) - max_reported} more vendor prefixes")

    return issues, deduction


def css_external_stylesheet(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect <link rel='stylesheet'> tags (stripped by all email clients)."""
    deduction = _css_param(config, "deduction_external_stylesheet", 0.25)

    matches = _LINK_STYLESHEET_RE.findall(raw_html)
    if not matches:
        return [], 0.0

    issues = [f"External stylesheet detected: {m[:80]}" for m in matches]
    return issues, deduction


def css_import_rule(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect @import rules (stripped by Gmail and most clients)."""
    deduction = _css_param(config, "deduction_import_rule", 0.20)

    blocks = _parse_css_blocks(raw_html)
    issues: list[str] = []
    for block in blocks:
        for m in _IMPORT_RE.finditer(block):
            line_start = block.rfind("\n", 0, m.start()) + 1
            line_end = block.find(";", m.start())
            if line_end == -1:
                line_end = block.find("\n", m.start())
            if line_end == -1:
                line_end = len(block)
            line = block[line_start : line_end + 1].strip()
            issues.append(f"@import rule: {line[:80]}")

    if not issues:
        return [], 0.0

    return issues, deduction


def css_important_overuse(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect excessive !important usage (may conflict with dark mode)."""
    threshold = int(_css_param(config, "important_threshold", 10))
    deduction = _css_param(config, "deduction_important_overuse", 0.10)

    all_css = "\n".join(_parse_css_blocks(raw_html) + _parse_inline_styles(raw_html))
    count = len(_IMPORTANT_RE.findall(all_css))

    if count <= threshold:
        return [], 0.0

    # Don't count !important inside dark mode media queries (those are expected).
    # Use brace-balancing to extract content of dark mode blocks, supporting
    # multi-condition queries like @media (min-width: 600px) and (prefers-color-scheme: dark).
    dark_mode_count = 0
    dark_media_start_re = re.compile(
        r"@media\s[^{]*prefers-color-scheme\s*:\s*dark[^{]*\{",
        re.IGNORECASE,
    )
    for block in _parse_css_blocks(raw_html):
        for dm_match in dark_media_start_re.finditer(block):
            # Walk forward from opening brace, balancing braces to find the end
            start = dm_match.end()
            depth = 1
            pos = start
            while pos < len(block) and depth > 0:
                if block[pos] == "{":
                    depth += 1
                elif block[pos] == "}":
                    depth -= 1
                pos += 1
            dark_content = block[start : pos - 1]
            dark_mode_count += len(_IMPORTANT_RE.findall(dark_content))
    non_dark_count = count - dark_mode_count

    if non_dark_count <= threshold:
        return [], 0.0

    issues = [
        f"{non_dark_count} !important declarations outside dark mode "
        f"(threshold: {threshold}) — may conflict with client dark mode injection"
    ]
    return issues, deduction


def css_non_inline_dependency(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect layout-critical CSS in <style> blocks without inline fallbacks."""
    max_reported = int(_css_param(config, "max_non_inline_reported", 5))
    deduction = _css_param(config, "deduction_non_inline", 0.10)

    style_blocks = _parse_css_blocks(raw_html)
    if not style_blocks:
        return [], 0.0

    all_block_css = "\n".join(style_blocks)
    inline_styles = _parse_inline_styles(raw_html)
    issues: list[str] = []

    for prop in sorted(_LAYOUT_CRITICAL_PROPS):
        # Use word boundary (or start-of-line/semicolon) to prevent partial matches
        # e.g. "color" must not match "background-color"
        prop_pattern = rf"(?<![a-zA-Z-]){re.escape(prop)}\s*:"
        prop_in_block = re.search(prop_pattern, all_block_css, re.IGNORECASE)
        if prop_in_block:
            prop_inline = any(
                re.search(prop_pattern, style, re.IGNORECASE) for style in inline_styles
            )
            if not prop_inline:
                issues.append(f"'{prop}' in <style> block only — no inline fallback for Gmail")

    if not issues:
        return [], 0.0

    reported = issues[:max_reported]
    if len(issues) > max_reported:
        reported.append(f"... and {len(issues) - max_reported} more")

    return reported, deduction


def css_syntax_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary of CSS syntax validation."""
    blocks = _parse_css_blocks(raw_html)
    inline = _parse_inline_styles(raw_html)
    all_css = "\n".join(blocks + inline)

    vendor_count = len(set(_VENDOR_PREFIX_RE.findall(all_css)))
    important_count = len(_IMPORTANT_RE.findall(all_css))
    external_count = len(_LINK_STYLESHEET_RE.findall(raw_html))
    import_count = len(_IMPORT_RE.findall(all_css))

    parts: list[str] = []
    if vendor_count:
        parts.append(f"{vendor_count} vendor prefixes")
    if important_count:
        parts.append(f"{important_count} !important")
    if external_count:
        parts.append(f"{external_count} external stylesheets")
    if import_count:
        parts.append(f"{import_count} @import rules")

    summary = f"CSS audit: {len(blocks)} style blocks, {len(inline)} inline styles"
    if parts:
        summary += f" — {', '.join(parts)}"

    return [summary], 0.0


# Register CSS syntax validation custom checks
register_custom_check("css_syntax_errors", css_syntax_errors)
register_custom_check("css_empty_declarations", css_empty_declarations)
register_custom_check("css_vendor_prefixes", css_vendor_prefixes)
register_custom_check("css_external_stylesheet", css_external_stylesheet)
register_custom_check("css_import_rule", css_import_rule)
register_custom_check("css_important_overuse", css_important_overuse)
register_custom_check("css_non_inline_dependency", css_non_inline_dependency)
register_custom_check("css_syntax_summary", css_syntax_summary)
