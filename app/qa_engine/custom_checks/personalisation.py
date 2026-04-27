# ruff: noqa: ARG001
"""Personalisation syntax custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.personalisation_validator import (
    ESPPlatform,
    analyze_personalisation,
)
from app.qa_engine.rule_engine import register_custom_check

# ---------------------------------------------------------------------------
# Personalisation Syntax Validation check functions
# ---------------------------------------------------------------------------


def _ps_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve personalisation config parameter."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def personalisation_mixed_platform(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect if multiple ESP platforms are used in same template."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.is_mixed_platform:
        deduction = _ps_param(config, "deduction_mixed_platform", 0.30)
        platforms = ", ".join(p.value for p in analysis.detected_platforms)
        return [f"Mixed platforms detected: {platforms}"], deduction
    return [], 0.0


def personalisation_unknown_platform(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag when personalisation tags exist but platform can't be identified."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform == ESPPlatform.UNKNOWN:
        deduction = _ps_param(config, "deduction_unknown_platform", 0.10)
        return ["Personalisation tags detected but ESP platform could not be identified"], deduction
    return [], 0.0


def personalisation_delimiter_balance(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check all personalisation delimiters are properly balanced."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    errors = analysis.unbalanced_delimiters
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_delimiter_unbalanced", 0.15)
    cap = int(_ps_param(config, "max_delimiter_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more delimiter issues")
    return issues, round(len(errors) * deduction, 4)


def personalisation_conditional_balance(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check conditional blocks (if/endif, IF/ENDIF, etc.) are balanced."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    errors = analysis.unbalanced_conditionals
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_conditional_unbalanced", 0.15)
    cap = int(_ps_param(config, "max_conditional_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more conditional issues")
    return issues, round(len(errors) * deduction, 4)


def personalisation_fallback_missing(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag output tags without fallback values."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    # Find output tags without fallbacks
    missing = [t for t in analysis.tags if t.tag_type == "output" and not t.has_fallback]
    if not missing:
        return [], 0.0
    deduction = _ps_param(config, "deduction_fallback_missing", 0.05)
    cap = int(_ps_param(config, "max_fallback_issues", 10))
    issues: list[str] = []
    for t in missing[:cap]:
        var = t.variable_name or t.raw[:40]
        issues.append(f"No fallback for '{var}' at line {t.line_number}")
    if len(missing) > cap:
        issues.append(f"... and {len(missing) - cap} more tags without fallbacks")
    return issues, round(len(missing) * deduction, 4)


def personalisation_fallback_empty(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag fallbacks that resolve to empty string."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    errors = analysis.empty_fallbacks
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_fallback_empty", 0.03)
    cap = int(_ps_param(config, "max_fallback_empty_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more empty fallbacks")
    return issues, round(len(errors) * deduction, 4)


def personalisation_liquid_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Validate Liquid syntax for Braze/Klaviyo templates."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform not in (ESPPlatform.BRAZE, ESPPlatform.KLAVIYO):
        return [], 0.0
    errors = analysis.syntax_errors
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_syntax_error", 0.10)
    cap = int(_ps_param(config, "max_syntax_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more syntax errors")
    return issues, round(len(errors) * deduction, 4)


def personalisation_ampscript_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Validate AMPscript syntax for SFMC templates."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform != ESPPlatform.SFMC:
        return [], 0.0
    errors = analysis.syntax_errors
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_syntax_error", 0.10)
    cap = int(_ps_param(config, "max_syntax_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more syntax errors")
    return issues, round(len(errors) * deduction, 4)


def personalisation_jssp_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Validate JSSP/EL syntax for Adobe Campaign templates."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform != ESPPlatform.ADOBE_CAMPAIGN:
        return [], 0.0
    errors = analysis.syntax_errors
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_syntax_error", 0.10)
    cap = int(_ps_param(config, "max_syntax_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more syntax errors")
    return issues, round(len(errors) * deduction, 4)


def personalisation_other_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Validate syntax for Mailchimp/HubSpot/Iterable templates."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform not in (
        ESPPlatform.MAILCHIMP,
        ESPPlatform.HUBSPOT,
        ESPPlatform.ITERABLE,
    ):
        return [], 0.0
    errors = analysis.syntax_errors
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_syntax_error", 0.10)
    cap = int(_ps_param(config, "max_syntax_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more syntax errors")
    return issues, round(len(errors) * deduction, 4)


def personalisation_nesting_depth(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag excessive conditional nesting (>3 levels)."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    errors = analysis.nested_depth_violations
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_nesting_depth", 0.03)
    cap = int(_ps_param(config, "max_nesting_issues", 3))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more nesting violations")
    return issues, round(len(errors) * deduction, 4)


def personalisation_summary_stats(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary — no deduction."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return ["Summary: No personalisation tags found"], 0.0

    platform = analysis.primary_platform.value
    parts = [f"Summary: {analysis.total_tags} tag(s), platform: {platform}"]
    if analysis.tags_with_fallback:
        parts.append(f"{analysis.tags_with_fallback} with fallback")
    if analysis.tags_without_fallback:
        parts.append(f"{analysis.tags_without_fallback} without fallback")
    return [", ".join(parts)], 0.0


# Register personalisation syntax custom checks
register_custom_check("personalisation_mixed_platform", personalisation_mixed_platform)
register_custom_check("personalisation_unknown_platform", personalisation_unknown_platform)
register_custom_check("personalisation_delimiter_balance", personalisation_delimiter_balance)
register_custom_check("personalisation_conditional_balance", personalisation_conditional_balance)
register_custom_check("personalisation_fallback_missing", personalisation_fallback_missing)
register_custom_check("personalisation_fallback_empty", personalisation_fallback_empty)
register_custom_check("personalisation_liquid_syntax", personalisation_liquid_syntax)
register_custom_check("personalisation_ampscript_syntax", personalisation_ampscript_syntax)
register_custom_check("personalisation_jssp_syntax", personalisation_jssp_syntax)
register_custom_check("personalisation_other_syntax", personalisation_other_syntax)
register_custom_check("personalisation_nesting_depth", personalisation_nesting_depth)
register_custom_check("personalisation_summary_stats", personalisation_summary_stats)
