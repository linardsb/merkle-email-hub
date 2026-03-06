"""HTML sanitization for component uploads.

Strips XSS vectors while preserving email-specific constructs
(MSO conditionals, dark mode CSS, inline styles).
"""

import re

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


def sanitize_component_html(html: str) -> str:
    """Strip XSS vectors from component HTML.

    Removes script tags, event handlers, javascript: protocol,
    dangerous tags (iframe, embed, object, form), and data: URIs.
    Preserves MSO conditional comments needed for Outlook rendering.
    Preserves @media prefers-color-scheme rules for dark mode.

    Args:
        html: HTML string to sanitize.

    Returns:
        Sanitized HTML string.
    """
    result = html
    result = _SCRIPT_TAG_RE.sub("", result)
    result = _EVENT_HANDLER_RE.sub("", result)
    result = _JS_PROTOCOL_RE.sub(r'\1=""', result)
    result = _DANGEROUS_TAG_RE.sub("", result)
    result = _DANGEROUS_SELF_CLOSING_RE.sub("", result)
    result = _DATA_URI_RE.sub(r'\1=""', result)
    return result
