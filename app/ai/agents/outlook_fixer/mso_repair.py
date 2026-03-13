"""Deterministic MSO repair functions for post-generation validation.

Attempts simple, safe fixes before falling back to LLM retry.
Only fixes structural issues that have unambiguous solutions.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.qa_engine.mso_parser import (
    MSOIssue,
    MSOValidationResult,
)

logger = get_logger(__name__)


def repair_mso_issues(html: str, result: MSOValidationResult) -> tuple[str, list[str]]:
    """Attempt deterministic repair of MSO issues.

    Only fixes issues with unambiguous solutions:
    - Missing MSO closers → append <![endif]-->
    - Missing xmlns:v/xmlns:o → inject into <html> tag
    - Orphaned MSO closers → remove extras

    Args:
        html: Generated HTML with MSO issues.
        result: Validation result from validate_mso_conditionals().

    Returns:
        Tuple of (repaired_html, list of repair descriptions).
    """
    repairs: list[str] = []
    repaired = html

    # Fix missing namespace declarations
    repaired, ns_repairs = _inject_missing_namespaces(repaired, result)
    repairs.extend(ns_repairs)

    # Fix unbalanced MSO conditionals
    repaired, balance_repairs = _balance_mso_conditionals(repaired, result)
    repairs.extend(balance_repairs)

    if repairs:
        logger.info(
            "agents.outlook_fixer.mso_repair_applied",
            repair_count=len(repairs),
            repairs=repairs,
        )

    return repaired, repairs


def _inject_missing_namespaces(html: str, result: MSOValidationResult) -> tuple[str, list[str]]:
    """Inject missing VML/Office namespace declarations on <html> tag."""
    repairs: list[str] = []

    if result.vml_element_count == 0:
        return html, repairs

    ns_issues = [i for i in result.issues if i.category == "namespace"]
    if not ns_issues:
        return html, repairs

    html_tag_re = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)
    match = html_tag_re.search(html)
    if not match:
        return html, repairs

    attrs = match.group(1)
    new_attrs = attrs

    if not result.has_vml_namespace:
        new_attrs += ' xmlns:v="urn:schemas-microsoft-com:vml"'
        repairs.append("Injected xmlns:v namespace on <html> tag")

    if not result.has_office_namespace:
        new_attrs += ' xmlns:o="urn:schemas-microsoft-com:office:office"'
        repairs.append("Injected xmlns:o namespace on <html> tag")

    if new_attrs != attrs:
        html = html[: match.start(1)] + new_attrs + html[match.end(1) :]

    return html, repairs


def _balance_mso_conditionals(html: str, result: MSOValidationResult) -> tuple[str, list[str]]:
    """Fix unbalanced MSO conditional openers/closers.

    Only handles the simple case: missing closers at end of document.
    Does NOT attempt to insert closers mid-document (too risky).
    """
    repairs: list[str] = []

    balance_issues = [i for i in result.issues if i.category == "balanced_pair"]
    if not balance_issues:
        return html, repairs

    # Missing closers — append before </body> or end of document
    if result.opener_count > result.closer_count:
        missing = result.opener_count - result.closer_count
        closers = "\n<![endif]-->" * missing

        # Insert before </body> if present, else append
        body_close_re = re.compile(r"</body>", re.IGNORECASE)
        body_match = body_close_re.search(html)
        if body_match:
            html = html[: body_match.start()] + closers + "\n" + html[body_match.start() :]
        else:
            html += closers

        repairs.append(f"Appended {missing} missing MSO closer(s) (<![endif]-->)")

    # Extra closers — remove from end (safest removal point)
    elif result.closer_count > result.opener_count:
        excess = result.closer_count - result.opener_count
        removed = 0
        for _ in range(excess):
            last_closer = html.rfind("<![endif]-->")
            if last_closer != -1:
                # Verify this closer doesn't have <!--<! prefix (non-MSO closer)
                prefix_start = max(0, last_closer - 4)
                if html[prefix_start:last_closer] != "<!--":
                    html = html[:last_closer] + html[last_closer + len("<![endif]-->") :]
                    removed += 1

        if removed:
            repairs.append(f"Removed {removed} orphaned MSO closer(s)")

    return html, repairs


def format_validation_errors(result: MSOValidationResult) -> str:
    """Format MSO validation issues as structured error context for LLM retry.

    Returns a prompt-ready string describing each issue with position hints.
    """
    if result.is_valid:
        return ""

    lines = ["Your generated HTML has MSO validation errors that must be fixed:\n"]

    by_category: dict[str, list[MSOIssue]] = {}
    for issue in result.issues:
        by_category.setdefault(issue.category, []).append(issue)

    category_labels = {
        "balanced_pair": "Unbalanced MSO Conditionals",
        "syntax": "Invalid Conditional Syntax",
        "vml_orphan": "VML Elements Outside MSO Blocks",
        "namespace": "Missing Namespace Declarations",
        "ghost_table": "Ghost Table Issues",
    }

    for cat, issues in by_category.items():
        label = category_labels.get(cat, cat)
        lines.append(f"### {label}")
        for issue in issues:
            pos_hint = f" (near char {issue.position})" if issue.position >= 0 else ""
            lines.append(f"- [{issue.severity.upper()}] {issue.message}{pos_hint}")
        lines.append("")

    lines.append(
        "Fix these specific issues. Ensure every <!--[if opens has a matching "
        "<![endif]-->, all VML elements are inside MSO blocks, and xmlns "
        "namespaces are declared when VML is present."
    )

    return "\n".join(lines)
