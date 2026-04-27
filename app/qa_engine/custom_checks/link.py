# ruff: noqa: ARG001
"""Link validation custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.link_parser import get_cached_link_result
from app.qa_engine.rule_engine import register_custom_check

# ─── Link Validation Custom Checks ─── (delegates to link_parser module)


def _link_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve a link check parameter from config."""
    if config:
        return float(config.params.get(key, default))
    return default


def link_non_https(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag non-HTTPS links (except localhost)."""
    deduction = _link_param(config, "deduction_http_link", 0.10)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "non_https"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_malformed_url(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag malformed URLs (missing scheme, netloc, path traversal)."""
    deduction = _link_param(config, "deduction_malformed_url", 0.15)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "malformed_url"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_blocked_protocol(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag javascript:/data:/vbscript: protocols."""
    deduction = _link_param(config, "deduction_blocked_protocol", 0.25)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "suspicious_protocol"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_empty_href(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag empty or fragment-only hrefs."""
    deduction = _link_param(config, "deduction_empty_href", 0.05)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "empty_href"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_template_balanced(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag unbalanced ESP template variable delimiters in hrefs."""
    deduction = _link_param(config, "deduction_template_unbalanced", 0.15)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "template_syntax"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_unencoded_chars(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag unencoded spaces or special characters in URLs."""
    deduction = _link_param(config, "deduction_unencoded", 0.05)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "unencoded_chars"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_double_encoded(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag double-encoded URL characters (e.g. %2520)."""
    deduction = _link_param(config, "deduction_double_encoded", 0.05)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "double_encoded"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_phishing_mismatch(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag links where display text URL domain differs from href domain."""
    deduction = _link_param(config, "deduction_phishing", 0.20)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "phishing_mismatch"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_has_any(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational: report if zero links found."""
    result = get_cached_link_result(raw_html)
    if result.total_links == 0:
        return ["No links found in email"], 0.0
    return [], 0.0


def link_accessible_text(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check links have visible text or image alt text."""
    deduction = _link_param(config, "deduction_no_link_text", 0.05)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for link in result.links:
        if link.text:
            continue
        # link.text comes from lxml text_content() which includes descendant
        # img alt text — so empty text means no visible text AND no img alt
        if link.href:
            if len(issues) < cap:
                issues.append(f"Link has no accessible text: {link.href[:60]}")
            total += deduction

    return issues, total


def link_vml_href(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check VML elements with href attributes in MSO conditional blocks."""
    from app.qa_engine.link_parser import _VML_HREF_RE

    deduction = _link_param(config, "deduction_vml_href", 0.10)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    issues: list[str] = []
    total = 0.0

    for match in _VML_HREF_RE.finditer(raw_html):
        vml_href = match.group(1)
        if vml_href:
            if len(issues) < cap:
                issues.append(
                    f"VML href found: {vml_href[:60]} — ensure it matches "
                    f"the corresponding <a> href (ESPs only rewrite <a> tags)"
                )
            total += deduction

    return issues, total


register_custom_check("link_non_https", link_non_https)
register_custom_check("link_malformed_url", link_malformed_url)
register_custom_check("link_blocked_protocol", link_blocked_protocol)
register_custom_check("link_empty_href", link_empty_href)
register_custom_check("link_template_balanced", link_template_balanced)
register_custom_check("link_unencoded_chars", link_unencoded_chars)
register_custom_check("link_double_encoded", link_double_encoded)
register_custom_check("link_phishing_mismatch", link_phishing_mismatch)
register_custom_check("link_has_any", link_has_any)
register_custom_check("link_accessible_text", link_accessible_text)
register_custom_check("link_vml_href", link_vml_href)
