"""Link parser and validator for email HTML.

Provides validate_links() for use by:
- QA link_validation check (via rule engine custom functions)
- Code Reviewer agent (direct import for link-focused reviews)

Parses <a> tags via lxml DOM, validates URLs via urllib.parse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from lxml.html import HtmlElement

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinkIssue:
    """A single link validation finding."""

    category: str  # "non_https" | "malformed_url" | "template_syntax" | "empty_href" |
    #               "suspicious_protocol" | "unencoded_chars" | "phishing_mismatch" |
    #               "double_encoded"
    message: str
    href: str = ""
    severity: str = "warning"  # "error" | "warning" | "info"


@dataclass(frozen=True)
class LinkInfo:
    """Parsed information about a single <a> tag."""

    href: str
    text: str = ""
    is_template: bool = False
    template_type: str = ""  # "liquid" | "ampscript" | "jssp" | ""
    has_img_child: bool = False


@dataclass
class LinkValidationResult:
    """Aggregate result of link validation."""

    issues: list[LinkIssue] = field(default_factory=lambda: list[LinkIssue]())
    links: list[LinkInfo] = field(default_factory=lambda: list[LinkInfo]())
    total_links: int = 0
    https_links: int = 0
    http_links: int = 0
    template_links: int = 0
    empty_hrefs: int = 0
    mailto_links: int = 0
    tel_links: int = 0
    anchor_links: int = 0


# ---------------------------------------------------------------------------
# Regex patterns (compiled once)
# ---------------------------------------------------------------------------

# ESP template variable patterns
_LIQUID_VAR_RE = re.compile(r"\{\{.*?\}\}", re.DOTALL)
_LIQUID_TAG_RE = re.compile(r"\{%.*?%\}", re.DOTALL)
_AMPSCRIPT_RE = re.compile(r"%%\[.*?\]%%", re.DOTALL)
_JSSP_RE = re.compile(r"<%=.*?%>", re.DOTALL)

# No regex needed for balance detection — use counting in _detect_template_type

# Dangerous/blocked protocols
_BLOCKED_PROTOCOLS = frozenset({"javascript", "data", "vbscript"})

# Unencoded characters that break email client links
_UNENCODED_SPACE_RE = re.compile(r"(?<!%20) (?!%)")  # Space not already encoded
_UNENCODED_SPECIAL_RE = re.compile(r"[<>\[\]{}|\\^`]")  # Must be encoded in URLs

# Double-encoded pattern (e.g. %2520 = double-encoded space)
_DOUBLE_ENCODED_RE = re.compile(r"%25[0-9A-Fa-f]{2}")

# Phishing: display text looks like a URL
_URL_IN_TEXT_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

# VML href attributes in MSO conditional comments
_VML_HREF_RE = re.compile(
    r"<v:(?:roundrect|rect|oval|shape)[^>]*\bhref\s*=\s*[\"']([^\"']*)[\"']",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Sub-validator functions
# ---------------------------------------------------------------------------


def _detect_template_type(href: str) -> tuple[str, bool]:
    """Detect ESP template syntax type and check delimiter balance.

    Returns:
        (type, is_balanced) where type is "liquid" | "ampscript" | "jssp" | "".
    """
    # Check Liquid {{ }} / {% %}
    has_liquid_var = bool(_LIQUID_VAR_RE.search(href))
    has_liquid_tag = bool(_LIQUID_TAG_RE.search(href))
    if has_liquid_var or has_liquid_tag:
        # Count openers vs closers
        open_count = href.count("{{") + href.count("{%")
        close_count = href.count("}}") + href.count("%}")
        return ("liquid", open_count == close_count)

    # Check AMPscript %%[ ]%%
    has_ampscript = bool(_AMPSCRIPT_RE.search(href))
    if has_ampscript:
        open_count = href.count("%%[")
        close_count = href.count("]%%")
        return ("ampscript", open_count == close_count)

    # Check JSSP <%= %>
    has_jssp = bool(_JSSP_RE.search(href))
    if has_jssp:
        open_count = href.count("<%=")
        close_count = href.count("%>")
        return ("jssp", open_count == close_count)

    # Check for unbalanced delimiters without matching pairs
    if "{{" in href or "}}" in href:
        return ("liquid", href.count("{{") == href.count("}}"))
    if "%%[" in href or "]%%" in href:
        return ("ampscript", href.count("%%[") == href.count("]%%"))
    if "<%=" in href or "%>" in href:
        return ("jssp", href.count("<%=") == href.count("%>"))

    return ("", True)


def _is_template_href(href: str) -> bool:
    """Check if href is entirely or primarily a template variable.

    Returns True if the href after stripping template syntax is empty
    or contains only whitespace/punctuation.
    """
    stripped = href.strip()
    if not stripped:
        return False

    # Remove all template syntax
    remaining = _LIQUID_VAR_RE.sub("", stripped)
    remaining = _LIQUID_TAG_RE.sub("", remaining)
    remaining = _AMPSCRIPT_RE.sub("", remaining)
    remaining = _JSSP_RE.sub("", remaining)

    # If nothing meaningful remains, it's a template-only href
    remaining = remaining.strip()
    return remaining == ""


def _validate_url_format(href: str) -> list[LinkIssue]:
    """Validate URL structure using urlparse. HTTP/HTTPS only."""
    issues: list[LinkIssue] = []
    parsed = urlparse(href)

    # Must have netloc for http/https
    if parsed.scheme in ("http", "https") and not parsed.netloc:
        issues.append(
            LinkIssue(
                category="malformed_url",
                message=f"URL missing domain: {href[:80]}",
                href=href,
            )
        )

    # Path traversal
    if "/../" in (parsed.path or "") or parsed.path.startswith("/../"):
        issues.append(
            LinkIssue(
                category="malformed_url",
                message=f"Path traversal in URL: {href[:80]}",
                href=href,
            )
        )

    return issues


def _check_encoding(href: str) -> list[LinkIssue]:
    """Check for unencoded or double-encoded characters in URLs."""
    issues: list[LinkIssue] = []

    # Unencoded spaces
    if _UNENCODED_SPACE_RE.search(href):
        issues.append(
            LinkIssue(
                category="unencoded_chars",
                message=f"Unencoded space in URL: {href[:80]}",
                href=href,
            )
        )

    # Unencoded special characters
    # Only check the path/query portion (after the netloc)
    parsed = urlparse(href)
    check_part = (parsed.path or "") + ("?" + parsed.query if parsed.query else "")
    if _UNENCODED_SPECIAL_RE.search(check_part):
        issues.append(
            LinkIssue(
                category="unencoded_chars",
                message=f"Unencoded special characters in URL: {href[:80]}",
                href=href,
            )
        )

    # Double-encoded (e.g. %2520)
    if _DOUBLE_ENCODED_RE.search(href):
        issues.append(
            LinkIssue(
                category="double_encoded",
                message=f"Double-encoded characters in URL: {href[:80]}",
                href=href,
            )
        )

    return issues


def _check_protocol(href: str) -> list[LinkIssue]:
    """Check for blocked or unknown protocols."""
    issues: list[LinkIssue] = []
    parsed = urlparse(href)

    scheme = parsed.scheme.lower()
    if not scheme:
        return issues

    if scheme in _BLOCKED_PROTOCOLS:
        issues.append(
            LinkIssue(
                category="suspicious_protocol",
                message=f"Blocked protocol '{scheme}:' in href: {href[:80]}",
                href=href,
                severity="error",
            )
        )

    return issues


def _check_empty_suspicious(href: str) -> list[LinkIssue]:
    """Flag empty, fragment-only, or javascript:void(0) hrefs."""
    issues: list[LinkIssue] = []

    if not href:
        issues.append(
            LinkIssue(
                category="empty_href",
                message="Empty href attribute",
                href=href,
            )
        )
    elif href == "#":
        issues.append(
            LinkIssue(
                category="empty_href",
                message="Fragment-only href='#' — link has no destination",
                href=href,
            )
        )
    elif href.lower().startswith("javascript:void"):
        issues.append(
            LinkIssue(
                category="suspicious_protocol",
                message=f"javascript:void in href: {href[:80]}",
                href=href,
                severity="error",
            )
        )

    return issues


def _check_phishing_mismatch(href: str, text: str) -> list[LinkIssue]:
    """Flag links where visible text URL domain differs from href domain."""
    issues: list[LinkIssue] = []

    if not text:
        return issues

    # Find URLs in the visible text
    text_urls = _URL_IN_TEXT_RE.findall(text)
    if not text_urls:
        return issues

    # Get the href domain
    href_parsed = urlparse(href)
    href_domain = (href_parsed.netloc or "").lower().removeprefix("www.")
    if not href_domain:
        return issues

    for text_url in text_urls:
        text_parsed = urlparse(str(text_url))
        text_domain = str(text_parsed.netloc or "").lower().removeprefix("www.")
        if text_domain and text_domain != href_domain:
            issues.append(
                LinkIssue(
                    category="phishing_mismatch",
                    message=(
                        f"Display text shows '{text_domain}' "
                        f"but href points to '{href_domain}' — phishing signal"
                    ),
                    href=href,
                    severity="error",
                )
            )
            break  # One phishing flag per link is enough

    return issues


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------


def validate_links(html: str, doc: HtmlElement | None = None) -> LinkValidationResult:
    """Validate all links in email HTML.

    Args:
        html: Raw HTML string.
        doc: Pre-parsed lxml document (optional, parsed from html if None).
    """
    result = LinkValidationResult()

    if not html or not html.strip():
        return result

    if doc is None:
        from lxml import html as lxml_html

        try:
            doc = lxml_html.document_fromstring(html)
        except Exception:
            logger.warning("link_parser.parse_failed", html_length=len(html))
            return result

    for a_tag in doc.iter("a"):
        href = (a_tag.get("href") or "").strip()
        text = (a_tag.text_content() or "").strip()
        result.total_links += 1

        # Detect template syntax
        tmpl_type, is_balanced = _detect_template_type(href)
        is_template = _is_template_href(href)
        has_img = any(True for _ in a_tag.iter("img"))

        link_info = LinkInfo(
            href=href,
            text=text,
            is_template=is_template,
            template_type=tmpl_type,
            has_img_child=has_img,
        )
        result.links.append(link_info)

        # 1. Empty/suspicious href
        if not href or href == "#":
            result.empty_hrefs += 1
            result.issues.extend(_check_empty_suspicious(href))
            continue

        # 2. Template syntax balance check
        if tmpl_type and not is_balanced:
            result.issues.append(
                LinkIssue(
                    category="template_syntax",
                    message=f"Unbalanced {tmpl_type} template syntax in href: {href[:80]}",
                    href=href,
                    severity="error",
                )
            )

        # 3. If entirely template, skip URL format checks
        if is_template:
            result.template_links += 1
            continue

        # 4. Protocol check
        result.issues.extend(_check_protocol(href))

        # 5. Count by protocol
        parsed = urlparse(href)
        if parsed.scheme == "https":
            result.https_links += 1
        elif parsed.scheme == "http":
            result.http_links += 1
            if "localhost" not in href and "127.0.0.1" not in href:
                result.issues.append(
                    LinkIssue(
                        category="non_https",
                        message=f"Non-HTTPS link: {href[:80]}",
                        href=href,
                    )
                )
        elif parsed.scheme == "mailto":
            result.mailto_links += 1
        elif parsed.scheme == "tel":
            result.tel_links += 1
        elif href.startswith("#"):
            result.anchor_links += 1
            continue  # Fragment-only anchors — skip further validation

        # 6. URL format validation (only for http/https)
        if parsed.scheme in ("http", "https"):
            result.issues.extend(_validate_url_format(href))

        # 7. Encoding check (http/https only)
        if parsed.scheme in ("http", "https"):
            result.issues.extend(_check_encoding(href))

        # 8. Phishing mismatch check
        result.issues.extend(_check_phishing_mismatch(href, text))

    logger.debug(
        "link_parser.validation_complete",
        total_links=result.total_links,
        https_links=result.https_links,
        http_links=result.http_links,
        template_links=result.template_links,
        issues=len(result.issues),
    )

    return result


# ---------------------------------------------------------------------------
# Caching layer for QA check integration
# ---------------------------------------------------------------------------

_link_cache: dict[str, LinkValidationResult] = {}


def get_cached_link_result(raw_html: str) -> LinkValidationResult:
    """Get cached link validation result, computing if not cached.

    Used by custom check functions to avoid re-parsing the same HTML
    across multiple rule evaluations within a single check run.
    """
    if raw_html not in _link_cache:
        _link_cache[raw_html] = validate_links(raw_html)
    return _link_cache[raw_html]


def clear_link_cache() -> None:
    """Clear the link validation cache. Called at start of each check run."""
    _link_cache.clear()
