"""Shared utilities for AI agents.

Provides HTML extraction from LLM responses and XSS sanitization.
Extracted from scaffolder and dark_mode agents to eliminate duplication.
"""

import re

import nh3

# ── HTML extraction from LLM responses ──

_CODE_BLOCK_RE = re.compile(
    r"```(?:html|HTML)?\s*\n(.*?)```",
    re.DOTALL,
)

# Tags allowed in email HTML output — covers standard email + Outlook/MSO
_ALLOWED_TAGS: set[str] = {
    # Structure
    "html",
    "head",
    "body",
    "meta",
    "title",
    "link",
    # Layout
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "td",
    "th",
    "caption",
    "colgroup",
    "col",
    "div",
    "span",
    "p",
    "br",
    "hr",
    "center",
    # Text
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "strike",
    "sub",
    "sup",
    "small",
    "big",
    "blockquote",
    "pre",
    "code",
    # Lists
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    # Media
    "img",
    "picture",
    "source",
    "video",
    # Links
    "a",
    # Style
    "style",
    # Accessibility
    "abbr",
    "address",
    "cite",
}

_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "*": {
        "class",
        "id",
        "style",
        "dir",
        "lang",
        "role",
        "aria-label",
        "aria-hidden",
        "aria-describedby",
        "aria-labelledby",
        "title",
        "align",
        "valign",
        "width",
        "height",
        "bgcolor",
        "background",
        "border",
        "cellpadding",
        "cellspacing",
    },
    "a": {"href", "target", "rel", "name"},
    "img": {"src", "alt", "loading", "srcset"},
    "td": {"colspan", "rowspan", "scope"},
    "th": {"colspan", "rowspan", "scope"},
    "meta": {"charset", "name", "content", "http-equiv"},
    "link": {"rel", "href", "type", "media"},
    "source": {"srcset", "media", "type"},
    "col": {"span"},
    "colgroup": {"span"},
}

# URL schemes allowed in href/src attributes
_ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto", "tel"}

# Regex to extract document structure — nh3 is a fragment sanitizer and strips these
_DOCTYPE_RE = re.compile(r"(<!DOCTYPE[^>]*>)\s*", re.IGNORECASE)
_HTML_OPEN_RE = re.compile(r"(<html\b[^>]*>)", re.IGNORECASE)
_HEAD_RE = re.compile(r"(<head\b[^>]*>)(.*?)(</head\s*>)", re.DOTALL | re.IGNORECASE)
_BODY_OPEN_RE = re.compile(r"(<body\b[^>]*>)", re.IGNORECASE)
_BODY_CLOSE_RE = re.compile(r"(</body\s*>)", re.IGNORECASE)


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


def _nh3_clean(fragment: str) -> str:
    """Run nh3 sanitization on an HTML fragment."""
    return nh3.clean(
        fragment,
        tags=_ALLOWED_TAGS,
        clean_content_tags={"script", "iframe", "embed", "object", "form"},
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel=None,
        strip_comments=False,
    )


def sanitize_html_xss(html: str) -> str:
    """Strip XSS vectors from generated HTML using allowlist-based sanitization.

    Uses nh3 (Rust-based HTML sanitizer) for robust protection against:
    - Script injection (tags, event handlers, javascript: protocol)
    - Dangerous tags (iframe, embed, object, form, svg with scripts)
    - Data URI attacks
    - Encoded/obfuscated XSS vectors

    Preserves email-safe HTML: tables, inline styles, MSO comments, dark mode CSS.
    Preserves document structure (DOCTYPE, html, head, body) since nh3 is a
    fragment sanitizer that strips document-level tags.

    Args:
        html: HTML string to sanitize.

    Returns:
        Sanitized HTML string.
    """
    # nh3 is a fragment sanitizer — it strips <!DOCTYPE>, <html>, <head>, <body>.
    # Email templates are full documents, so we extract the document shell,
    # sanitize head and body content separately, then reassemble.
    doctype_m = _DOCTYPE_RE.search(html)
    html_open_m = _HTML_OPEN_RE.search(html)
    head_m = _HEAD_RE.search(html)
    body_open_m = _BODY_OPEN_RE.search(html)
    body_close_m = _BODY_CLOSE_RE.search(html)

    is_full_document = doctype_m or (html_open_m and body_open_m)

    if not is_full_document:
        return _nh3_clean(html)

    # Reassemble document from parts
    parts: list[str] = []
    if doctype_m:
        parts.append(doctype_m.group(1))
        parts.append("\n")
    if html_open_m:
        parts.append(html_open_m.group(1))
        parts.append("\n")
    if head_m:
        head_content = _nh3_clean(head_m.group(2))
        parts.append(head_m.group(1))
        parts.append(head_content)
        parts.append(head_m.group(3))
        parts.append("\n")
    if body_open_m:
        parts.append(body_open_m.group(1))
        parts.append("\n")
        # Extract body content between <body> and </body>
        body_start = body_open_m.end()
        body_end = body_close_m.start() if body_close_m else len(html)
        body_content = html[body_start:body_end]
        parts.append(_nh3_clean(body_content))
        parts.append("\n")
    if body_close_m:
        parts.append(body_close_m.group(1))
        parts.append("\n")
    if html_open_m:
        parts.append("</html>\n")

    return "".join(parts)
