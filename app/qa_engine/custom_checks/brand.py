# ruff: noqa: ARG001
"""Brand compliance custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

import re

from lxml.html import HtmlElement

from app.qa_engine.brand_analyzer import analyze_brand
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import register_custom_check

# ---------------------------------------------------------------------------
# Custom check functions — brand compliance
# ---------------------------------------------------------------------------

_GENERIC_FONTS = frozenset(
    {
        "serif",
        "sans-serif",
        "monospace",
        "cursive",
        "fantasy",
        "system-ui",
        "ui-serif",
        "ui-sans-serif",
        "ui-monospace",
    }
)


def _brand_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve a brand compliance config parameter."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def brand_color_compliance(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check CSS colors against allowed brand palette."""
    allowed_raw: list[str] = config.params.get("allowed_colors", []) if config else []
    if not allowed_raw:
        return [], 0.0

    allowed = {c.strip().lower() for c in allowed_raw}
    # Expand 3-char hex
    expanded: set[str] = set()
    for c in allowed:
        expanded.add(c)
        if re.match(r"^#[0-9a-f]{3}$", c):
            expanded.add(f"#{c[1] * 2}{c[2] * 2}{c[3] * 2}")
    allowed = expanded

    analysis = analyze_brand(doc, raw_html)
    off_brand = analysis.colors_found - allowed

    if not off_brand:
        return [], 0.0

    deduction_each = _brand_param(config, "deduction_off_brand_color", 0.20)
    cap = int(_brand_param(config, "max_color_issues_reported", 10))
    issues: list[str] = []
    for color in sorted(off_brand):
        if len(issues) < cap:
            issues.append(f"Off-brand color: {color}")

    return issues, deduction_each * len(off_brand)


def brand_font_compliance(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check font-family declarations against approved brand fonts."""
    required_raw: list[str] = config.params.get("required_fonts", []) if config else []
    if not required_raw:
        return [], 0.0

    approved = {f.strip().lower() for f in required_raw}

    analysis = analyze_brand(doc, raw_html)
    non_brand = analysis.fonts_found - approved - _GENERIC_FONTS

    if not non_brand:
        return [], 0.0

    deduction_each = _brand_param(config, "deduction_wrong_font", 0.15)
    cap = int(_brand_param(config, "max_font_issues_reported", 5))
    issues: list[str] = []
    for font in sorted(non_brand):
        if len(issues) < cap:
            issues.append(f"Non-brand font: {font}")

    return issues, deduction_each * len(non_brand)


def brand_required_footer(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check footer section is present (if required by brand rules)."""
    required: list[str] = config.params.get("required_elements", []) if config else []
    if "footer" not in required:
        return [], 0.0

    analysis = analyze_brand(doc, raw_html)
    if analysis.has_footer:
        return [], 0.0

    deduction = _brand_param(config, "deduction_missing_footer", 0.25)
    return ["Required footer section missing"], deduction


def brand_required_logo(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check brand logo image is present (if required by brand rules)."""
    required: list[str] = config.params.get("required_elements", []) if config else []
    if "logo" not in required:
        return [], 0.0

    analysis = analyze_brand(doc, raw_html)
    if analysis.has_logo:
        return [], 0.0

    deduction = _brand_param(config, "deduction_missing_logo", 0.25)
    return ["Required brand logo missing"], deduction


def brand_required_unsubscribe(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check unsubscribe link is present (if required by brand rules)."""
    required: list[str] = config.params.get("required_elements", []) if config else []
    if "unsubscribe" not in required:
        return [], 0.0

    analysis = analyze_brand(doc, raw_html)
    if analysis.has_unsubscribe:
        return [], 0.0

    deduction = _brand_param(config, "deduction_missing_unsubscribe", 0.25)
    return ["Required unsubscribe link missing"], deduction


def brand_forbidden_patterns(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check for forbidden text patterns in email content."""
    patterns_raw: list[str] = config.params.get("forbidden_patterns", []) if config else []
    if not patterns_raw:
        return [], 0.0

    analysis = analyze_brand(doc, raw_html)
    text_lower = analysis.raw_text.lower()

    deduction_each = _brand_param(config, "deduction_forbidden_pattern", 0.20)
    cap = int(_brand_param(config, "max_pattern_issues_reported", 5))
    issues: list[str] = []
    total = 0.0

    for pattern in patterns_raw:
        try:
            if re.search(re.escape(pattern.lower()), text_lower):
                if len(issues) < cap:
                    issues.append(f'Forbidden pattern found: "{pattern}"')
                total += deduction_each
        except re.error:
            continue

    return issues, total


def brand_compliance_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational brand compliance summary — no deduction."""
    analysis = analyze_brand(doc, raw_html)
    parts: list[str] = [
        f"Brand compliance: {len(analysis.colors_found)} colors, "
        f"{len(analysis.fonts_found)} fonts found; "
        f"footer={'yes' if analysis.has_footer else 'no'}, "
        f"logo={'yes' if analysis.has_logo else 'no'}, "
        f"unsubscribe={'yes' if analysis.has_unsubscribe else 'no'}"
    ]
    return parts, 0.0


# Register brand compliance custom checks
register_custom_check("brand_color_compliance", brand_color_compliance)
register_custom_check("brand_font_compliance", brand_font_compliance)
register_custom_check("brand_required_footer", brand_required_footer)
register_custom_check("brand_required_logo", brand_required_logo)
register_custom_check("brand_required_unsubscribe", brand_required_unsubscribe)
register_custom_check("brand_forbidden_patterns", brand_forbidden_patterns)
register_custom_check("brand_compliance_summary", brand_compliance_summary)
