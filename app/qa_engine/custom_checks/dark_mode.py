# ruff: noqa: ARG001
"""Dark mode custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

import re

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.dark_mode_parser import (
    _COLOR_PROPERTIES as _DM_COLOR_PROPERTIES,
)
from app.qa_engine.dark_mode_parser import (
    _hex_to_luminance,
    _parse_css_color,
    get_cached_dm_result,
)
from app.qa_engine.rule_engine import register_custom_check

# ─── Dark Mode Semantic Checks ─── (delegates to dark_mode_parser module)


def _dm_param(config: QACheckConfig | None, key: str, default: float = 0.0) -> float:
    """Resolve a dark mode check parameter from config or default."""
    if config:
        return float(config.params.get(key, default))
    return default


def dm_color_scheme_meta(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check color-scheme meta tag is present, valid, and includes 'dark'."""
    deduction = float(_dm_param(config, "deduction_missing_color_scheme", 0.15))
    result = get_cached_dm_result(raw_html)
    if not result.meta_tags.has_color_scheme:
        return (["Missing <meta name='color-scheme' content='light dark'>"], deduction)
    if "dark" not in result.meta_tags.content_value.lower():
        return (["color-scheme meta present but content doesn't include 'dark'"], deduction)
    return ([], 0.0)


def dm_supported_color_schemes(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check supported-color-schemes companion meta tag."""
    deduction = float(_dm_param(config, "deduction_missing_supported", 0.05))
    result = get_cached_dm_result(raw_html)
    if not result.meta_tags.has_supported_color_schemes:
        return (
            ["Missing <meta name='supported-color-schemes'> companion tag for older Apple Mail"],
            deduction,
        )
    return ([], 0.0)


def dm_css_color_scheme_property(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check CSS color-scheme property on :root or html."""
    deduction = float(_dm_param(config, "deduction_missing_css_color_scheme", 0.05))
    result = get_cached_dm_result(raw_html)
    if not result.meta_tags.has_css_color_scheme:
        return (
            ["Missing 'color-scheme: light dark' CSS property on :root"],
            deduction,
        )
    return ([], 0.0)


def dm_meta_placement(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check color-scheme meta tag is in <head> not <body>."""
    deduction = float(_dm_param(config, "deduction_meta_misplaced", 0.10))
    result = get_cached_dm_result(raw_html)
    # Only flag if meta exists AND is misplaced
    if result.meta_tags.has_color_scheme and not result.meta_tags.color_scheme_in_head:
        return (["color-scheme meta tag found in <body> instead of <head>"], deduction)
    return ([], 0.0)


def dm_media_query_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check @media (prefers-color-scheme: dark) block exists."""
    deduction = float(_dm_param(config, "deduction_no_media_query", 0.25))
    result = get_cached_dm_result(raw_html)
    if not result.media_queries:
        return (["No @media (prefers-color-scheme: dark) block found"], deduction)
    return ([], 0.0)


def dm_media_query_has_colors(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode media query contains color declarations."""
    deduction = float(_dm_param(config, "deduction_empty_media_query", 0.20))
    result = get_cached_dm_result(raw_html)
    if not result.media_queries:
        return ([], 0.0)  # No media query — handled by dm_media_query_present
    if not any(mq.has_color_props for mq in result.media_queries):
        return (
            ["prefers-color-scheme: dark block exists but contains no color properties"],
            deduction,
        )
    return ([], 0.0)


def dm_media_query_important(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode color declarations use !important."""
    deduction = float(_dm_param(config, "deduction_missing_important", 0.10))
    cap = int(_dm_param(config, "max_dm_issues_reported", 5))
    result = get_cached_dm_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for mq in result.media_queries:
        for decl in mq.declarations:
            if decl.property in _DM_COLOR_PROPERTIES and not decl.has_important:
                if len(issues) < cap:
                    issues.append(f"Dark mode '{decl.property}: {decl.value}' missing !important")
                total += deduction

    return issues, total


def dm_ogsc_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check [data-ogsc] Outlook.com text color selectors exist."""
    deduction = float(_dm_param(config, "deduction_no_ogsc", 0.10))
    result = get_cached_dm_result(raw_html)
    if not any(s.selector_type == "ogsc" for s in result.outlook_selectors):
        return (["No [data-ogsc] selectors — Outlook.com will force-invert text colors"], deduction)
    return ([], 0.0)


def dm_ogsb_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check [data-ogsb] Outlook.com background selectors exist."""
    deduction = float(_dm_param(config, "deduction_no_ogsb", 0.10))
    result = get_cached_dm_result(raw_html)
    if not any(s.selector_type == "ogsb" for s in result.outlook_selectors):
        return (
            ["No [data-ogsb] selectors — Outlook.com will force-invert background colors"],
            deduction,
        )
    return ([], 0.0)


def dm_outlook_selectors_have_content(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check Outlook selectors contain actual CSS declarations."""
    deduction = float(_dm_param(config, "deduction_empty_outlook", 0.10))
    result = get_cached_dm_result(raw_html)
    if not result.outlook_selectors:
        return ([], 0.0)  # No selectors — handled by ogsc/ogsb presence checks
    empty = [s for s in result.outlook_selectors if not s.has_declarations]
    if empty:
        return (
            ["Outlook [data-ogsc]/[data-ogsb] selectors present but contain no CSS declarations"],
            deduction,
        )
    return ([], 0.0)


def dm_no_invisible_text(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check for near-identical foreground/background in dark mode color pairs."""
    deduction = float(_dm_param(config, "deduction_invisible_text", 0.20))
    cap = int(_dm_param(config, "max_dm_issues_reported", 3))
    result = get_cached_dm_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for pair in result.color_pairs:
        if pair.contrast_ratio > 0 and pair.contrast_ratio < 1.5:
            if len(issues) < cap:
                issues.append(
                    f"Near-invisible text in dark mode: {pair.selector} "
                    f"{pair.css_property} contrast ratio {pair.contrast_ratio}:1"
                )
            total += deduction

    return issues, total


def dm_contrast_ratio(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode color pairs meet WCAG AA 4.5:1 contrast ratio."""
    deduction = float(_dm_param(config, "deduction_low_contrast", 0.10))
    cap = int(_dm_param(config, "max_dm_issues_reported", 5))
    result = get_cached_dm_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for pair in result.color_pairs:
        if pair.contrast_ratio > 0 and pair.contrast_ratio < 4.5 and pair.contrast_ratio >= 1.5:
            if len(issues) < cap:
                issues.append(
                    f"Low contrast in dark mode: {pair.selector} "
                    f"{pair.css_property} ratio {pair.contrast_ratio}:1 (need 4.5:1)"
                )
            total += deduction

    return issues, total


def dm_backgrounds_are_dark(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode background colors have low luminance (are actually dark)."""
    deduction = float(_dm_param(config, "deduction_light_dark_bg", 0.10))
    cap = int(_dm_param(config, "max_dm_issues_reported", 3))
    result = get_cached_dm_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for pair in result.color_pairs:
        if pair.css_property in {"background-color", "background"}:
            dark_hex = _parse_css_color(pair.dark_value)
            if dark_hex:
                luminance = _hex_to_luminance(dark_hex)
                if luminance > 0.4:
                    if len(issues) < cap:
                        issues.append(
                            f"Dark mode background {pair.dark_value} on {pair.selector} "
                            f"has high luminance ({luminance:.2f}) — should be dark"
                        )
                    total += deduction

    return issues, total


def dm_image_swap_alt(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode swap images have empty alt text."""
    deduction = float(_dm_param(config, "deduction_swap_img_alt", 0.05))
    cap = int(_dm_param(config, "max_dm_issues_reported", 3))
    issues: list[str] = []
    total = 0.0

    # Find images with dark-mode-related classes that are hidden by default
    for img in doc.iter("img"):
        classes = (img.get("class") or "").lower()
        style = (img.get("style") or "").lower()
        if any(c in classes for c in ("dark-img", "dark-image", "dark-logo", "dark_img")) and (
            "display: none" in style or "display:none" in style
        ):
            alt = img.get("alt")
            if alt is not None and alt != "" and len(issues) < cap:
                issues.append(
                    "Dark mode swap image should have alt='' to avoid "
                    "duplicate screen reader announcements"
                )
                total += deduction

    return issues, total


def dm_hidden_img_mso(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check hidden dark mode images include mso-hide:all for Outlook."""
    deduction = float(_dm_param(config, "deduction_no_mso_hide", 0.05))
    cap = int(_dm_param(config, "max_dm_issues_reported", 3))
    issues: list[str] = []
    total = 0.0

    for img in doc.iter("img"):
        classes = (img.get("class") or "").lower()
        style = img.get("style") or ""
        if (
            any(c in classes for c in ("dark-img", "dark-image", "dark-logo", "dark_img"))
            and ("display: none" in style.lower() or "display:none" in style.lower())
            and not re.search(r"mso-hide\s*:\s*all", style, re.IGNORECASE)
            and len(issues) < cap
        ):
            issues.append(
                "Dark mode swap image hidden by default should include 'mso-hide: all' for Outlook"
            )
            total += deduction

    return issues, total


def dm_any_support_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check that at least some dark mode support exists."""
    deduction = float(_dm_param(config, "deduction_no_dark_mode", 0.30))
    result = get_cached_dm_result(raw_html)
    has_meta = result.meta_tags.has_color_scheme
    has_media = len(result.media_queries) > 0
    has_outlook = len(result.outlook_selectors) > 0
    if not has_meta and not has_media and not has_outlook:
        return (
            [
                "No dark mode support detected — no meta tags, no media queries, no Outlook selectors"
            ],
            deduction,
        )
    return ([], 0.0)


register_custom_check("dm_color_scheme_meta", dm_color_scheme_meta)
register_custom_check("dm_supported_color_schemes", dm_supported_color_schemes)
register_custom_check("dm_css_color_scheme_property", dm_css_color_scheme_property)
register_custom_check("dm_meta_placement", dm_meta_placement)
register_custom_check("dm_media_query_present", dm_media_query_present)
register_custom_check("dm_media_query_has_colors", dm_media_query_has_colors)
register_custom_check("dm_media_query_important", dm_media_query_important)
register_custom_check("dm_ogsc_present", dm_ogsc_present)
register_custom_check("dm_ogsb_present", dm_ogsb_present)
register_custom_check("dm_outlook_selectors_have_content", dm_outlook_selectors_have_content)
register_custom_check("dm_no_invisible_text", dm_no_invisible_text)
register_custom_check("dm_contrast_ratio", dm_contrast_ratio)
register_custom_check("dm_backgrounds_are_dark", dm_backgrounds_are_dark)
register_custom_check("dm_image_swap_alt", dm_image_swap_alt)
register_custom_check("dm_hidden_img_mso", dm_hidden_img_mso)
register_custom_check("dm_any_support_present", dm_any_support_present)
