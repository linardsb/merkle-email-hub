"""HTML context offloading — replace blind truncation with structural summarization.

Instead of `html[:12000]` which loses footer/preheader content on complex emails,
this module provides `prepare_html_context()` which returns full HTML when short,
or a summary + first/last sections for long emails.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "HtmlSummary",
    "extract_section",
    "prepare_html_context",
    "summarize_html",
]

# Patterns to detect in email HTML
_MSO_RE = re.compile(r"<!--\[if\s+(?:gte\s+)?mso", re.IGNORECASE)
_VML_RE = re.compile(r"<v:", re.IGNORECASE)
_DARK_MODE_RE = re.compile(
    r"prefers-color-scheme\s*:\s*dark|\.darkmode|data-og[sb]c", re.IGNORECASE
)
_PERSONALIZATION_RE = re.compile(r"\{\{|<%|<amp-|%\{|\{\%|{{%|AMPscript|HubL", re.IGNORECASE)
_COMPONENT_REF_RE = re.compile(r'<component\s+src="components/')

# Section boundaries — common structural markers in email HTML
_SECTION_MARKERS = [
    re.compile(r"<!--\s*(?:START|BEGIN)\s+(\w[\w\s]*?)-->", re.IGNORECASE),
    re.compile(r'<tr[^>]*class="[^"]*section[^"]*"', re.IGNORECASE),
    re.compile(r"<!--\s*SECTION:\s*(\w+)", re.IGNORECASE),
    re.compile(
        r'<td[^>]*(?:class|id)="[^"]*(?:header|hero|body|content|footer|preheader)[^"]*"',
        re.IGNORECASE,
    ),
]


@dataclass(frozen=True)
class HtmlSummary:
    """Structural summary of email HTML."""

    section_count: int = 0
    line_count: int = 0
    byte_size: int = 0
    detected_patterns: tuple[str, ...] = ()
    section_boundaries: tuple[int, ...] = ()


def summarize_html(html: str) -> HtmlSummary:
    """Deterministic pattern scan of email HTML.

    Returns structural metadata without modifying the HTML.
    """
    patterns: list[str] = []

    if _MSO_RE.search(html):
        patterns.append("mso_conditionals")
    if _VML_RE.search(html):
        patterns.append("vml")
    if _DARK_MODE_RE.search(html):
        patterns.append("dark_mode")
    if _PERSONALIZATION_RE.search(html):
        patterns.append("personalization")
    if _COMPONENT_REF_RE.search(html):
        patterns.append("component_refs")

    # Detect section boundaries
    boundaries: list[int] = []
    for marker_re in _SECTION_MARKERS:
        for match in marker_re.finditer(html):
            boundaries.append(match.start())

    boundaries = sorted(set(boundaries))

    return HtmlSummary(
        section_count=max(len(boundaries), 1),
        line_count=html.count("\n") + 1,
        byte_size=len(html.encode("utf-8")),
        detected_patterns=tuple(patterns),
        section_boundaries=tuple(boundaries),
    )


def extract_section(html: str, section_idx: int) -> str:
    """Extract a section by index from email HTML.

    Uses detected section boundaries. Returns empty string if index is out of range.
    """
    summary = summarize_html(html)
    bounds = summary.section_boundaries

    if not bounds or section_idx < 0:
        return ""

    if section_idx >= len(bounds):
        return ""

    start = bounds[section_idx]
    end = bounds[section_idx + 1] if section_idx + 1 < len(bounds) else len(html)

    return html[start:end]


def prepare_html_context(html: str, *, max_chars: int = 8000) -> str:
    """Prepare HTML for inclusion in agent context.

    If HTML is under max_chars, returns it in full.
    Otherwise, returns a structural summary + first and last sections
    to preserve both header/preheader and footer content.

    Args:
        html: Raw email HTML.
        max_chars: Character threshold for full inclusion.

    Returns:
        HTML context string (full or summarized).
    """
    if len(html) <= max_chars:
        return html

    summary = summarize_html(html)

    # Build summary header
    header_lines = [
        f"[HTML Summary: {summary.byte_size:,} bytes, {summary.line_count} lines, "
        f"~{summary.section_count} sections]",
    ]
    if summary.detected_patterns:
        header_lines.append(f"[Patterns: {', '.join(summary.detected_patterns)}]")

    # Allocate space: 40% first section, 40% last section, 20% summary overhead
    section_budget = (max_chars - 500) // 2  # 500 chars for summary header

    # Guard: if sections would overlap, just return truncated with summary header
    if section_budget * 2 >= len(html):
        return "\n".join(header_lines) + "\n\n" + html

    # First section: from start of HTML
    first_section = html[:section_budget]

    # Last section: from end of HTML (captures footer/preheader-at-bottom)
    last_section = html[-section_budget:]

    parts = [
        "\n".join(header_lines),
        "\n--- FIRST SECTION ---\n",
        first_section,
        "\n--- LAST SECTION ---\n",
        last_section,
    ]

    return "\n".join(parts)
