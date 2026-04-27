# ruff: noqa: ARG001
"""MSO/Outlook fallback custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.mso_parser import get_cached_result
from app.qa_engine.rule_engine import register_custom_check

# ─── MSO Fallback Custom Checks ─── (delegates to mso_parser module)


def _mso_param(config: QACheckConfig | None, key: str, default: float = 0.0) -> float:
    """Resolve an MSO check parameter from config or default."""
    if config:
        return float(config.params.get(key, default))
    return default


def mso_balanced_pairs(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check MSO conditional opener/closer balance."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "balanced_pair"]
    deduction = _mso_param(config, "deduction_unbalanced_pair", 0.25) * len(issues)
    return issues, deduction


def mso_conditional_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check MSO conditional expression syntax validity."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "syntax"]
    deduction = _mso_param(config, "deduction_invalid_syntax", 0.15) * len(issues)
    return issues, deduction


def mso_vml_nesting(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check VML elements are inside MSO conditional blocks."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "vml_orphan"]
    deduction = _mso_param(config, "deduction_vml_orphan", 0.20) * len(issues)
    return issues, deduction


def mso_namespace_validation(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check VML/Office namespace declarations when VML elements are present."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "namespace"]
    deduction = _mso_param(config, "deduction_missing_namespace", 0.15) * len(issues)
    return issues, deduction


def mso_ghost_table_validation(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check ghost table structure in MSO conditional blocks."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "ghost_table"]
    deduction = _mso_param(config, "deduction_ghost_table_issue", 0.10) * len(issues)
    return issues, deduction


def mso_conditionals_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check that MSO conditional comments exist."""
    result = get_cached_result(raw_html)
    if result.opener_count == 0:
        deduction = _mso_param(config, "deduction_no_mso", 0.30)
        return ["No MSO conditional comments for Outlook fallbacks"], deduction
    return [], 0.0


def mso_namespaces_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check that VML/Office namespace declarations exist."""
    result = get_cached_result(raw_html)
    if not result.has_vml_namespace and not result.has_office_namespace:
        deduction = _mso_param(config, "deduction_no_namespaces", 0.20)
        return ["No VML/Office namespace declarations"], deduction
    return [], 0.0


register_custom_check("mso_balanced_pairs", mso_balanced_pairs)
register_custom_check("mso_conditional_syntax", mso_conditional_syntax)
register_custom_check("mso_vml_nesting", mso_vml_nesting)
register_custom_check("mso_namespace_validation", mso_namespace_validation)
register_custom_check("mso_ghost_table_validation", mso_ghost_table_validation)
register_custom_check("mso_conditionals_present", mso_conditionals_present)
register_custom_check("mso_namespaces_present", mso_namespaces_present)
