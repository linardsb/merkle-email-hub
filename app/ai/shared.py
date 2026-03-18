"""Shared utilities for AI agents.

Provides HTML extraction from LLM responses and XSS sanitization.
Extracted from scaffolder and dark_mode agents to eliminate duplication.
"""

import re
from dataclasses import dataclass

import nh3

# ── HTML extraction from LLM responses ──

# ── Confidence extraction from LLM output ──

_CONFIDENCE_RE = re.compile(r"<!--\s*CONFIDENCE:\s*([\d.]+)\s*-->")


def extract_confidence(html: str) -> float | None:
    """Extract self-assessed confidence from an LLM HTML comment.

    Looks for ``<!-- CONFIDENCE: 0.XX -->`` and clamps to [0.0, 1.0].
    Returns None if the comment is absent or malformed.
    """
    match = _CONFIDENCE_RE.search(html)
    if not match:
        return None
    try:
        return max(0.0, min(1.0, float(match.group(1))))
    except ValueError:
        return None


def strip_confidence_comment(html: str) -> str:
    """Remove the confidence HTML comment from output."""
    return _CONFIDENCE_RE.sub("", html)


# ── HTML extraction from LLM responses ──

_CODE_BLOCK_RE = re.compile(
    r"```(?:html|HTML)?\s*\n(.*?)```",
    re.DOTALL,
)

# Tags allowed in email HTML output — covers standard email + Outlook/MSO
_BASE_ALLOWED_TAGS: set[str] = {
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

_BASE_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
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
_BASE_ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto", "tel"}

# ── Restricted tag/attribute sets for per-agent profiles ──

_CONTENT_TAGS: set[str] = {"p", "span", "strong", "em", "b", "i", "a", "br", "ul", "ol", "li"}

_CONTENT_ATTRIBUTES: dict[str, set[str]] = {
    "*": {"class", "style", "dir"},
    "a": {"href", "target"},
}


@dataclass(frozen=True)
class SanitizationProfile:
    """Per-agent HTML sanitization configuration."""

    name: str
    allowed_tags: set[str]
    allowed_attributes: dict[str, set[str]]
    allowed_url_schemes: set[str]


PROFILES: dict[str, SanitizationProfile] = {
    "default": SanitizationProfile(
        name="default",
        allowed_tags=_BASE_ALLOWED_TAGS,
        allowed_attributes=_BASE_ALLOWED_ATTRIBUTES,
        allowed_url_schemes=_BASE_ALLOWED_URL_SCHEMES,
    ),
    "scaffolder": SanitizationProfile(
        name="scaffolder",
        allowed_tags=_BASE_ALLOWED_TAGS,
        allowed_attributes=_BASE_ALLOWED_ATTRIBUTES,
        allowed_url_schemes=_BASE_ALLOWED_URL_SCHEMES,
    ),
    "content": SanitizationProfile(
        name="content",
        allowed_tags=_CONTENT_TAGS,
        allowed_attributes=_CONTENT_ATTRIBUTES,
        allowed_url_schemes=_BASE_ALLOWED_URL_SCHEMES,
    ),
    "dark_mode": SanitizationProfile(
        name="dark_mode",
        allowed_tags=_BASE_ALLOWED_TAGS,
        allowed_attributes=_BASE_ALLOWED_ATTRIBUTES,
        allowed_url_schemes=_BASE_ALLOWED_URL_SCHEMES,
    ),
    "accessibility": SanitizationProfile(
        name="accessibility",
        allowed_tags=_BASE_ALLOWED_TAGS,
        allowed_attributes={
            **_BASE_ALLOWED_ATTRIBUTES,
            "*": _BASE_ALLOWED_ATTRIBUTES.get("*", set())
            | {
                "aria-live",
                "aria-atomic",
                "aria-relevant",
                "aria-busy",
                "aria-owns",
                "aria-controls",
                "aria-expanded",
                "aria-selected",
                "aria-pressed",
                "aria-checked",
                "aria-disabled",
                "aria-invalid",
                "aria-required",
                "aria-placeholder",
                "aria-roledescription",
                "aria-current",
                "aria-sort",
                "aria-colcount",
                "aria-rowcount",
                "tabindex",
            },
        },
        allowed_url_schemes=_BASE_ALLOWED_URL_SCHEMES,
    ),
    "personalisation": SanitizationProfile(
        name="personalisation",
        allowed_tags=_BASE_ALLOWED_TAGS,
        allowed_attributes=_BASE_ALLOWED_ATTRIBUTES,
        allowed_url_schemes=_BASE_ALLOWED_URL_SCHEMES,
    ),
    "outlook_fixer": SanitizationProfile(
        name="outlook_fixer",
        allowed_tags=_BASE_ALLOWED_TAGS,
        allowed_attributes=_BASE_ALLOWED_ATTRIBUTES,
        allowed_url_schemes=_BASE_ALLOWED_URL_SCHEMES,
    ),
    "code_reviewer": SanitizationProfile(
        name="code_reviewer",
        allowed_tags=set(),  # Returns JSON, not HTML
        allowed_attributes={},
        allowed_url_schemes=set(),
    ),
    "innovation": SanitizationProfile(
        name="innovation",
        allowed_tags=_BASE_ALLOWED_TAGS
        | {"form", "input", "button", "select", "option", "textarea", "label"},
        allowed_attributes={
            **_BASE_ALLOWED_ATTRIBUTES,
            "input": {"type", "name", "value", "placeholder", "checked", "disabled", "required"},
            "button": {"type", "name", "value", "disabled"},
            "select": {"name", "multiple", "disabled", "required"},
            "option": {"value", "selected", "disabled"},
            "textarea": {"name", "rows", "cols", "placeholder", "disabled", "required"},
            "label": {"for"},
            "form": {"action", "method"},
        },
        allowed_url_schemes=_BASE_ALLOWED_URL_SCHEMES,
    ),
}

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


# ── VML extraction helpers for Outlook Fixer ──

_VML_BLOCK_RE = re.compile(
    r"(<!--\[if\s+(?:gte\s+)?mso.*?\]>.*?<!\[endif\]-->)",
    re.DOTALL | re.IGNORECASE,
)
_VML_PLACEHOLDER = "<!--VML_BLOCK_{idx}-->"


def _extract_vml_blocks(html: str) -> tuple[str, list[str]]:
    """Extract VML/MSO conditional blocks before sanitization.

    nh3 doesn't handle VML namespace tags (v:rect, v:roundrect, etc.).
    We extract them, sanitize the rest, then restore.
    """
    blocks: list[str] = []

    def _replace(m: re.Match[str]) -> str:
        blocks.append(m.group(1))
        return _VML_PLACEHOLDER.format(idx=len(blocks) - 1)

    stripped = _VML_BLOCK_RE.sub(_replace, html)
    return stripped, blocks


def _restore_vml_blocks(html: str, blocks: list[str]) -> str:
    """Restore previously extracted VML blocks after sanitization."""
    for idx, block in enumerate(blocks):
        html = html.replace(_VML_PLACEHOLDER.format(idx=idx), block)
    return html


def _nh3_clean(fragment: str, profile: SanitizationProfile | None = None) -> str:
    """Run nh3 sanitization on an HTML fragment."""
    p = profile or PROFILES["default"]
    # Don't clean form tags if the profile allows them
    clean_content = {"script", "iframe", "embed", "object"}
    if "form" not in p.allowed_tags:
        clean_content.add("form")
    return nh3.clean(
        fragment,
        tags=p.allowed_tags,
        clean_content_tags=clean_content,
        attributes=p.allowed_attributes,
        url_schemes=p.allowed_url_schemes,
        link_rel=None,
        strip_comments=False,
    )


def sanitize_html_xss(html: str, profile: str = "default") -> str:
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
        profile: Sanitization profile name (matches agent_name). Defaults to "default".

    Returns:
        Sanitized HTML string.
    """
    p = PROFILES.get(profile, PROFILES["default"])

    # VML extraction — profiles with full email tags may contain MSO conditionals
    # that nh3 would mangle (VML namespace tags like v:rect, v:roundrect)
    _VML_PROFILES = {"outlook_fixer", "scaffolder", "dark_mode", "default", "personalisation"}
    vml_blocks: list[str] = []
    if profile in _VML_PROFILES:
        html, vml_blocks = _extract_vml_blocks(html)

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
        result = _nh3_clean(html, profile=p)
        if vml_blocks:
            result = _restore_vml_blocks(result, vml_blocks)
        return result

    # Reassemble document from parts
    parts: list[str] = []
    if doctype_m:
        parts.append(doctype_m.group(1))
        parts.append("\n")
    if html_open_m:
        parts.append(html_open_m.group(1))
        parts.append("\n")
    if head_m:
        head_content = _nh3_clean(head_m.group(2), profile=p)
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
        parts.append(_nh3_clean(body_content, profile=p))
        parts.append("\n")
    if body_close_m:
        parts.append(body_close_m.group(1))
        parts.append("\n")
    if html_open_m:
        parts.append("</html>\n")

    result = "".join(parts)
    if vml_blocks:
        result = _restore_vml_blocks(result, vml_blocks)
    return result
