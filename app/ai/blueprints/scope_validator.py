"""Scope validator — enforces per-agent modification constraints on retry.

Compares pre-fix and post-fix HTML to detect out-of-scope changes.
Uses lxml for lightweight structural comparison.
"""

from __future__ import annotations

from dataclasses import dataclass

from lxml import html as lxml_html

from app.ai.blueprints.protocols import AllowedScope
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ScopeViolation:
    """A single scope violation detected in fixer output."""

    description: str
    violation_type: (
        str  # "tag_removed", "tag_added", "structure_changed", "text_changed", "style_changed"
    )


def validate_scope(
    pre_html: str,
    post_html: str,
    scope: AllowedScope,
    agent_name: str,
) -> list[ScopeViolation]:
    """Compare pre/post HTML and return violations of the allowed scope.

    Returns empty list if all changes are within scope.
    """
    violations: list[ScopeViolation] = []

    try:
        pre_doc = lxml_html.fromstring(pre_html)
        post_doc = lxml_html.fromstring(post_html)
    except Exception:
        logger.warning("blueprint.scope_validator.parse_failed", agent=agent_name)
        return []  # Can't validate if we can't parse

    if scope.styles_only:
        pre_tags = _extract_tag_structure(pre_doc)
        post_tags = _extract_tag_structure(post_doc)
        if pre_tags != post_tags:
            violations.append(
                ScopeViolation(
                    description=f"{agent_name} modified HTML structure (only styles allowed)",
                    violation_type="structure_changed",
                )
            )

        pre_text = _extract_text_content(pre_doc)
        post_text = _extract_text_content(post_doc)
        if pre_text != post_text:
            violations.append(
                ScopeViolation(
                    description=f"{agent_name} modified text content (only styles allowed)",
                    violation_type="text_changed",
                )
            )

    if scope.additive_only:
        pre_counts = _count_tags(pre_doc)
        post_counts = _count_tags(post_doc)
        for tag, count in pre_counts.items():
            post_count = post_counts.get(tag, 0)
            if post_count < count:
                violations.append(
                    ScopeViolation(
                        description=f"{agent_name} removed {count - post_count} <{tag}> element(s) (additive only)",
                        violation_type="tag_removed",
                    )
                )

    if scope.text_only:
        pre_tags = _extract_tag_structure(pre_doc)
        post_tags = _extract_tag_structure(post_doc)
        if pre_tags != post_tags:
            violations.append(
                ScopeViolation(
                    description=f"{agent_name} modified HTML structure (text only allowed)",
                    violation_type="structure_changed",
                )
            )

    if scope.structure_only:
        pre_links = _extract_stylesheet_links(pre_doc)
        post_links = _extract_stylesheet_links(post_doc)
        new_links = post_links - pre_links
        if new_links:
            violations.append(
                ScopeViolation(
                    description=f"{agent_name} added external stylesheets: {new_links}",
                    violation_type="style_changed",
                )
            )

    return violations


def _extract_tag_structure(doc: lxml_html.HtmlElement) -> list[str]:
    """Extract ordered list of tag names (structural fingerprint)."""
    return [el.tag for el in doc.iter() if isinstance(el.tag, str)]


def _extract_text_content(doc: lxml_html.HtmlElement) -> str:
    """Extract all text content, ignoring <style> block inner text.

    Note: el.tail (text after </style>) IS included since it's not CSS.
    """
    parts: list[str] = []
    for el in doc.iter():
        # Skip inner text of <style> elements (CSS content), but keep tail
        if not (isinstance(el.tag, str) and el.tag == "style") and el.text:
            parts.append(el.text.strip())
        if el.tail:
            parts.append(el.tail.strip())
    return " ".join(parts)


def _count_tags(doc: lxml_html.HtmlElement) -> dict[str, int]:
    """Count occurrences of each tag."""
    counts: dict[str, int] = {}
    for el in doc.iter():
        if isinstance(el.tag, str):
            counts[el.tag] = counts.get(el.tag, 0) + 1
    return counts


def _extract_stylesheet_links(doc: lxml_html.HtmlElement) -> set[str]:
    """Extract href values from <link rel="stylesheet"> elements."""
    links: set[str] = set()
    for el in doc.iter("link"):
        if el.get("rel") == "stylesheet" and el.get("href"):
            links.add(el.get("href", ""))
    return links
