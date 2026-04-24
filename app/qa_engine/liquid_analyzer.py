"""Liquid template analysis — cached structural analysis of Liquid syntax."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_LIQUID_TAG_RE = re.compile(r"\{%[-~]?\s*(.*?)\s*[-~]?%\}", re.DOTALL)
_LIQUID_OUTPUT_RE = re.compile(r"\{\{[-~]?\s*(.*?)\s*[-~]?\}\}", re.DOTALL)
_LIQUID_COMMENT_RE = re.compile(
    r"\{%[-~]?\s*comment\s*[-~]?%\}.*?\{%[-~]?\s*endcomment\s*[-~]?%\}", re.DOTALL
)
_LIQUID_RAW_RE = re.compile(r"\{%[-~]?\s*raw\s*[-~]?%\}.*?\{%[-~]?\s*endraw\s*[-~]?%\}", re.DOTALL)

# Braze-specific patterns
_BRAZE_CONNECTED_CONTENT_RE = re.compile(r"\{%\s*connected_content\b", re.IGNORECASE)
_BRAZE_CONTENT_BLOCK_RE = re.compile(r"\{\{\s*content_blocks\.\$\{", re.IGNORECASE)
_BRAZE_ABORT_RE = re.compile(r"\{%\s*abort_message\b", re.IGNORECASE)

# Common Liquid filters
KNOWN_FILTERS: set[str] = {
    "abs",
    "append",
    "at_least",
    "at_most",
    "capitalize",
    "ceil",
    "compact",
    "concat",
    "date",
    "default",
    "divided_by",
    "downcase",
    "escape",
    "escape_once",
    "first",
    "floor",
    "join",
    "last",
    "lstrip",
    "map",
    "minus",
    "modulo",
    "newline_to_br",
    "plus",
    "prepend",
    "remove",
    "remove_first",
    "replace",
    "replace_first",
    "reverse",
    "round",
    "rstrip",
    "size",
    "slice",
    "sort",
    "sort_natural",
    "split",
    "strip",
    "strip_html",
    "strip_newlines",
    "times",
    "truncate",
    "truncatewords",
    "uniq",
    "upcase",
    "url_decode",
    "url_encode",
    "where",
}

# Block tags that require end tags
_BLOCK_TAGS: set[str] = {
    "if",
    "unless",
    "for",
    "case",
    "capture",
    "comment",
    "raw",
    "tablerow",
}


@dataclass
class LiquidAnalysis:
    """Structural analysis of Liquid template syntax."""

    tags_found: list[str] = field(default_factory=list[str])
    filters_used: list[str] = field(default_factory=list[str])
    variables: list[str] = field(default_factory=list[str])
    nesting_depth: int = 0
    is_braze: bool = False
    parse_errors: list[str] = field(default_factory=list[str])


def _extract_filters(expression: str) -> list[str]:
    """Extract filter names from a Liquid output expression."""
    filters: list[str] = []
    parts = expression.split("|")
    for part in parts[1:]:  # Skip the variable itself
        filter_name = part.strip().split(":")[0].strip().split(" ")[0].strip()
        if filter_name:
            filters.append(filter_name)
    return filters


def _extract_variable(expression: str) -> str:
    """Extract the base variable name from a Liquid output expression."""
    base = expression.split("|")[0].strip()
    return base.split(".")[0].strip()


def analyze_liquid(html: str) -> LiquidAnalysis:
    """Analyze Liquid template syntax in HTML.

    Returns structural analysis of Liquid tags, filters, variables,
    nesting depth, and Braze-specific features.
    """
    analysis = LiquidAnalysis()

    # Detect Braze-specific extensions
    if (
        _BRAZE_CONNECTED_CONTENT_RE.search(html)
        or _BRAZE_CONTENT_BLOCK_RE.search(html)
        or _BRAZE_ABORT_RE.search(html)
    ):
        analysis.is_braze = True

    # Strip raw blocks and comments for analysis
    stripped = _LIQUID_RAW_RE.sub("", html)
    stripped = _LIQUID_COMMENT_RE.sub("", stripped)

    # Extract tags
    tag_stack: list[str] = []
    max_depth = 0

    for match in _LIQUID_TAG_RE.finditer(stripped):
        tag_content = match.group(1).strip()
        tag_name = tag_content.split()[0] if tag_content else ""

        if not tag_name:
            continue

        analysis.tags_found.append(tag_name)

        # Track nesting
        if tag_name in _BLOCK_TAGS:
            tag_stack.append(tag_name)
            max_depth = max(max_depth, len(tag_stack))
        elif tag_name.startswith("end"):
            expected = tag_name[3:]
            if tag_stack and tag_stack[-1] == expected:
                tag_stack.pop()
            elif tag_stack:
                analysis.parse_errors.append(
                    f"Mismatched end tag: {{% {tag_name} %}} (expected end{tag_stack[-1]})"
                )
                # Try to pop anyway to recover
                tag_stack.pop()
            else:
                analysis.parse_errors.append(
                    f"Unexpected end tag: {{% {tag_name} %}} with no open block"
                )

    # Report unclosed blocks
    for unclosed in tag_stack:
        analysis.parse_errors.append(
            f"Unclosed block: {{% {unclosed} %}} missing {{% end{unclosed} %}}"
        )

    analysis.nesting_depth = max_depth

    # Extract outputs (variables and filters)
    for match in _LIQUID_OUTPUT_RE.finditer(stripped):
        expression = match.group(1).strip()
        if not expression:
            continue

        # Extract variable
        var_name = _extract_variable(expression)
        if var_name and var_name not in analysis.variables:
            analysis.variables.append(var_name)

        # Extract filters
        filters = _extract_filters(expression)
        for f in filters:
            if f not in analysis.filters_used:
                analysis.filters_used.append(f)

    return analysis


def clear_liquid_cache() -> None:
    """No-op kept for API compatibility. Analysis is no longer cached."""
