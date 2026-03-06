"""Shared utilities for AI agents.

Provides HTML extraction from LLM responses and XSS sanitization.
Extracted from scaffolder and dark_mode agents to eliminate duplication.
"""

import re

# ── Compiled regex patterns for HTML extraction and XSS sanitization ──

_CODE_BLOCK_RE = re.compile(
    r"```(?:html|HTML)?\s*\n(.*?)```",
    re.DOTALL,
)

_SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.DOTALL | re.IGNORECASE)
_EVENT_HANDLER_RE = re.compile(r"""\s+on\w+=\s*(?:"[^"]*"|'[^']*'|[^\s>]*)""", re.IGNORECASE)
_JS_PROTOCOL_RE = re.compile(r"""(href|src)\s{0,5}=\s{0,5}["']?\s{0,5}javascript:""", re.IGNORECASE)
_DANGEROUS_TAG_RE = re.compile(
    r"<(iframe|embed|object|form)\b[^>]{0,1000}>.*?</\1\s*>",
    re.DOTALL | re.IGNORECASE,
)
_DANGEROUS_SELF_CLOSING_RE = re.compile(
    r"<(iframe|embed|object)\b[^>]{0,1000}/?>",
    re.IGNORECASE,
)
_DATA_URI_RE = re.compile(r"""(href|src)\s{0,5}=\s{0,5}["']?\s{0,5}data:""", re.IGNORECASE)


def extract_html(content: str) -> str:
    """Extract HTML from markdown code blocks.

    Looks for ```html ... ``` blocks. Falls back to raw content
    if no code block is found.

    Args:
        content: Raw LLM response text.

    Returns:
        Extracted HTML string.
    """
    match = _CODE_BLOCK_RE.search(content)
    if match:
        return match.group(1).strip()
    return content.strip()


def sanitize_html_xss(html: str) -> str:
    """Strip XSS vectors from generated HTML.

    Removes script tags, event handlers, javascript: protocol,
    dangerous tags (iframe, embed, object, form), and data: URIs.
    Preserves MSO conditional comments needed for Outlook rendering.

    Args:
        html: HTML string to sanitize.

    Returns:
        Sanitized HTML string.
    """
    result = html

    # Remove <script> tags and their content
    result = _SCRIPT_TAG_RE.sub("", result)

    # Remove event handlers (onclick, onload, etc.)
    result = _EVENT_HANDLER_RE.sub("", result)

    # Remove javascript: protocol
    result = _JS_PROTOCOL_RE.sub(r'\1=""', result)

    # Remove dangerous tags with content
    result = _DANGEROUS_TAG_RE.sub("", result)

    # Remove self-closing dangerous tags
    result = _DANGEROUS_SELF_CLOSING_RE.sub("", result)

    # Remove data: URIs
    result = _DATA_URI_RE.sub(r'\1=""', result)

    return result
