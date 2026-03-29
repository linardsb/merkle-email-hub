"""Deterministic post-processing for Code Reviewer actionability.

Validates issue format, enriches with ontology data, tags responsible agents,
and identifies non-actionable suggestions for retry.
"""

import re
from typing import Any, cast

from app.ai.agents.code_reviewer.schemas import CodeReviewIssue, ResponsibleAgent
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Agent responsibility mapping ──
# Keywords in rule/message that indicate a specialist agent should handle it
_AGENT_KEYWORDS: dict[str, list[str]] = {
    "outlook_fixer": [
        "mso-",
        "mso_",
        "<!--[if mso",
        "<!--[if gte mso",
        "vml",
        "v:rect",
        "v:roundrect",
        "v:oval",
        "v:shape",
        "v:fill",
        "v:textbox",
        "ghost table",
        "xmlns:v",
        "xmlns:o",
        "xmlns:w",
    ],
    "dark_mode": [
        "color-scheme",
        "prefers-color-scheme",
        "data-ogsc",
        "data-ogsb",
        "dark mode",
        "dark-mode",
        "light-dark(",
    ],
    "accessibility": [
        "alt text",
        "alt=",
        "role=",
        "aria-",
        "lang=",
        "wcag",
        "heading",
        "contrast",
        "screen reader",
        "tabindex",
    ],
    "personalisation": [
        "liquid",
        "ampscript",
        "%%[",
        "]%%",
        "{{",
        "}}",
        "merge tag",
        "*|",
        "|*",
        "hubl",
        "handlebars",
    ],
    "scaffolder": [
        "table structure",
        "layout table",
        "missing doctype",
        "html skeleton",
        "email structure",
    ],
}

# ── Patterns that indicate a suggestion is NOT actionable ──
_VAGUE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^consider\b", re.IGNORECASE),
    re.compile(r"^you (?:should|could|might|may)\b", re.IGNORECASE),
    re.compile(r"^(?:try|look into|review|check)\b", re.IGNORECASE),
    re.compile(r"^it (?:is|would be) (?:better|recommended|advisable)\b", re.IGNORECASE),
    re.compile(r"ensure that\b", re.IGNORECASE),
    re.compile(r"^avoid\b", re.IGNORECASE),
]

# Minimum suggestion length for actionable content
_MIN_SUGGESTION_LENGTH = 15


def detect_responsible_agent(issue: CodeReviewIssue) -> str:
    """Detect which specialist agent should handle this issue.

    Checks rule ID and message text against keyword maps.
    Returns 'code_reviewer' if no specialist match found.
    """
    searchable = f"{issue.rule} {issue.message} {issue.suggestion or ''}".lower()
    for agent, keywords in _AGENT_KEYWORDS.items():
        if any(kw in searchable for kw in keywords):
            return agent
    return "code_reviewer"


def is_actionable(issue: CodeReviewIssue) -> bool:
    """Check if an issue has a sufficiently actionable suggestion.

    Actionable means:
    1. Has a non-empty suggestion
    2. Suggestion is not a vague directive
    3. Suggestion meets minimum length
    """
    if not issue.suggestion:
        return False

    suggestion = issue.suggestion.strip()
    if len(suggestion) < _MIN_SUGGESTION_LENGTH:
        return False

    # Check for vague patterns
    return all(not pattern.search(suggestion) for pattern in _VAGUE_PATTERNS)


def format_non_actionable_for_retry(issues: list[CodeReviewIssue]) -> str:
    """Format non-actionable issues for LLM retry.

    Only includes the issues that need reformatting, not the full HTML.
    """
    non_actionable = [i for i in issues if not is_actionable(i)]
    if not non_actionable:
        return ""

    parts = [
        "The following issues have vague suggestions. Rewrite each suggestion in "
        "concrete 'change X to Y' format. Include the current problematic value, "
        "the specific fix, and which email clients are affected.\n"
    ]

    for idx, issue in enumerate(non_actionable, 1):
        parts.append(
            f"\n{idx}. [{issue.severity}] {issue.rule}: {issue.message}\n"
            f"   Current suggestion: {issue.suggestion or '(none)'}\n"
            f"   → Rewrite with: current_value, fix_value, affected_clients"
        )

    parts.append(
        "\n\nRespond with ONLY a JSON array of the rewritten issues in the same "
        'format: [{"rule": "...", "severity": "...", "line_hint": N, '
        '"message": "...", "suggestion": "...", "current_value": "...", '
        '"fix_value": "...", "affected_clients": ["..."]}]'
    )

    return "\n".join(parts)


def validate_and_enrich_issues(
    issues: list[CodeReviewIssue],
) -> tuple[list[CodeReviewIssue], list[str]]:
    """Validate issue format and enrich with agent tagging.

    Returns:
        Tuple of (enriched issues, actionability warnings).
    """
    enriched: list[CodeReviewIssue] = []
    warnings: list[str] = []

    non_actionable_count = 0

    for issue in issues:
        # Tag responsible agent
        agent = detect_responsible_agent(issue)

        # Check actionability
        if not is_actionable(issue):
            non_actionable_count += 1
            warnings.append(f"[actionability] {issue.rule}: suggestion is vague or missing")

        enriched.append(
            CodeReviewIssue(
                rule=issue.rule,
                severity=issue.severity,
                line_hint=issue.line_hint,
                message=issue.message,
                suggestion=issue.suggestion,
                current_value=issue.current_value,
                fix_value=issue.fix_value,
                affected_clients=issue.affected_clients,
                responsible_agent=cast(ResponsibleAgent, agent),
            )
        )

    if non_actionable_count > 0:
        total = len(issues)
        pct = round((1 - non_actionable_count / total) * 100) if total else 0
        warnings.insert(
            0,
            f"[actionability] {pct}% actionable ({total - non_actionable_count}/{total})",
        )

    return enriched, warnings


def enrich_with_qa_results(
    issues: list[CodeReviewIssue],
    qa_results: list[Any],
) -> tuple[list[CodeReviewIssue], list[str]]:
    """Cross-check LLM issues against QA engine results.

    Adds warnings for:
    - Issues the QA engine found that the LLM missed

    Args:
        issues: LLM-generated issues.
        qa_results: QA check results from running checks on input HTML.

    Returns:
        Tuple of (same issues, additional cross-check warnings).
    """
    warnings: list[str] = []

    # Map QA check names to keywords that would appear in related LLM issue rules/messages
    qa_to_keywords: dict[str, list[str]] = {
        "css_support": ["css", "unsupported", "client-support", "vendor"],
        "html_validation": ["nesting", "invalid", "structure", "unclosed", "tag"],
        "file_size": ["file-size", "size", "clipping", "102kb", "bloat", "base64"],
        "link_validation": ["link", "href", "url", "mailto"],
        "spam_score": ["spam", "trigger", "hidden", "display:none"],
        "fallback": ["mso", "conditional", "vml", "ghost", "outlook"],
        "dark_mode": ["dark", "color-scheme", "prefers-color-scheme", "ogsc"],
        "accessibility": ["alt", "aria", "wcag", "role", "lang", "contrast", "heading"],
    }

    # Build searchable text from all LLM issues
    all_issue_text = " ".join(f"{i.rule} {i.message}".lower() for i in issues)

    for result in qa_results:
        check_name = getattr(result, "check_name", "")
        passed = getattr(result, "passed", True)
        keywords = qa_to_keywords.get(check_name)

        if not passed and keywords:
            # Check if any keyword from this QA domain appears in LLM issue text
            covered = any(kw in all_issue_text for kw in keywords)
            if not covered:
                warnings.append(
                    f"[qa_cross_check] QA '{check_name}' failed but no LLM issues in related domain"
                )

    return issues, warnings
