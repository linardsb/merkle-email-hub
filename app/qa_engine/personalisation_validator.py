"""Personalisation syntax analysis for email HTML.

Detects ESP platforms, extracts personalisation tags, validates delimiter
balance, checks fallback presence, and flags mixed-platform usage.

L4 Reference: docs/esp_personalisation/
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from typing import Final

from app.core.logging import get_logger

logger = get_logger(__name__)


class ESPPlatform(StrEnum):
    BRAZE = "braze"
    SFMC = "sfmc"
    ADOBE_CAMPAIGN = "adobe"
    KLAVIYO = "klaviyo"
    MAILCHIMP = "mailchimp"
    HUBSPOT = "hubspot"
    ITERABLE = "iterable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PersonalisationTag:
    """Single personalisation tag found in HTML."""

    platform: ESPPlatform
    raw: str
    tag_type: str  # "output" | "logic" | "comment" | "block"
    has_fallback: bool
    line_number: int
    variable_name: str


@dataclass(frozen=True)
class PersonalisationAnalysis:
    """Cached analysis result for an HTML document."""

    detected_platforms: list[ESPPlatform]
    primary_platform: ESPPlatform
    tags: list[PersonalisationTag]
    total_tags: int
    tags_with_fallback: int
    tags_without_fallback: int
    unbalanced_delimiters: list[str]
    unbalanced_conditionals: list[str]
    nested_depth_violations: list[str]
    is_mixed_platform: bool
    has_personalisation: bool
    syntax_errors: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    empty_fallbacks: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]


# ---------------------------------------------------------------------------
# Platform Detection
# ---------------------------------------------------------------------------

# Patterns ordered by uniqueness (most distinctive first)
_SFMC_PATTERN: Final = re.compile(r"%%\[|%%=")
_MAILCHIMP_PATTERN: Final = re.compile(r"\*\|[A-Z_]+\|\*")
_ADOBE_PATTERN: Final = re.compile(r"<%[= ]")
# Bounded quantifiers prevent polynomial backtracking (py/polynomial-redos).
_ITERABLE_CATALOG: Final = re.compile(r"\[\[[^\]]{1,500}\]\]")
_ITERABLE_HELPERS: Final = re.compile(r"\{\{#(?:if|each|unless)\b|\{\{defaultIfEmpty\b")
_BRAZE_DOLLAR: Final = re.compile(r"\{\{\s{0,10}\$\{")
_BRAZE_CONNECTED: Final = re.compile(r"\{%\s{0,10}(?:connected_content|content_blocks)\b")
_KLAVIYO_LOOKUP: Final = re.compile(r"\|\s{0,10}lookup\s{0,10}:|person\.")
_HUBSPOT_CONTACT: Final = re.compile(r"contact\.[a-z_]{1,100}\s{0,10}\|\s{0,10}default\s{0,10}\(")
_GENERIC_TEMPLATE: Final = re.compile(r"\{\{[^}]{1,2000}\}\}|\{%[^%]{1,2000}%\}")


def detect_platform(raw_html: str) -> tuple[ESPPlatform, float]:
    """Detect ESP platform from HTML content."""
    if _SFMC_PATTERN.search(raw_html):
        return ESPPlatform.SFMC, 0.95
    if _MAILCHIMP_PATTERN.search(raw_html):
        return ESPPlatform.MAILCHIMP, 0.95
    if _ADOBE_PATTERN.search(raw_html):
        return ESPPlatform.ADOBE_CAMPAIGN, 0.90
    if _ITERABLE_CATALOG.search(raw_html) and _GENERIC_TEMPLATE.search(raw_html):
        return ESPPlatform.ITERABLE, 0.85
    if _ITERABLE_HELPERS.search(raw_html):
        return ESPPlatform.ITERABLE, 0.85
    if _BRAZE_DOLLAR.search(raw_html):
        return ESPPlatform.BRAZE, 0.90
    if _BRAZE_CONNECTED.search(raw_html):
        return ESPPlatform.BRAZE, 0.85
    if _KLAVIYO_LOOKUP.search(raw_html):
        return ESPPlatform.KLAVIYO, 0.80
    if _HUBSPOT_CONTACT.search(raw_html):
        return ESPPlatform.HUBSPOT, 0.80
    if _GENERIC_TEMPLATE.search(raw_html):
        return ESPPlatform.UNKNOWN, 0.30
    return ESPPlatform.UNKNOWN, 0.0


def detect_all_platforms(raw_html: str) -> list[ESPPlatform]:
    """Detect ALL platforms present in the HTML (for mixed-platform detection)."""
    platforms: list[ESPPlatform] = []
    has_sfmc = _SFMC_PATTERN.search(raw_html) is not None
    has_mailchimp = _MAILCHIMP_PATTERN.search(raw_html) is not None
    has_adobe = _ADOBE_PATTERN.search(raw_html) is not None
    has_braze = (_BRAZE_DOLLAR.search(raw_html) or _BRAZE_CONNECTED.search(raw_html)) is not None
    has_iterable = bool(
        _ITERABLE_HELPERS.search(raw_html)
        or (_ITERABLE_CATALOG.search(raw_html) and _GENERIC_TEMPLATE.search(raw_html))
    )
    has_klaviyo = _KLAVIYO_LOOKUP.search(raw_html) is not None
    has_hubspot = _HUBSPOT_CONTACT.search(raw_html) is not None
    has_generic_template = _GENERIC_TEMPLATE.search(raw_html) is not None

    if has_sfmc:
        platforms.append(ESPPlatform.SFMC)
    if has_mailchimp:
        platforms.append(ESPPlatform.MAILCHIMP)
    if has_adobe:
        platforms.append(ESPPlatform.ADOBE_CAMPAIGN)
    if has_braze:
        platforms.append(ESPPlatform.BRAZE)
    if has_iterable:
        platforms.append(ESPPlatform.ITERABLE)
    if has_klaviyo:
        platforms.append(ESPPlatform.KLAVIYO)
    if has_hubspot:
        platforms.append(ESPPlatform.HUBSPOT)

    # If generic {{ }}/{% %} template syntax is present alongside a non-template
    # platform (SFMC, Mailchimp, Adobe), flag as mixed — the template syntax
    # likely belongs to a different ESP (Liquid/Django/HubL/Handlebars)
    non_template_platforms = {ESPPlatform.SFMC, ESPPlatform.MAILCHIMP, ESPPlatform.ADOBE_CAMPAIGN}
    if has_generic_template and platforms and all(p in non_template_platforms for p in platforms):
        platforms.append(ESPPlatform.UNKNOWN)

    return platforms


# ---------------------------------------------------------------------------
# Tag Extraction
# ---------------------------------------------------------------------------

_TAG_PATTERNS: Final[dict[ESPPlatform, list[tuple[str, re.Pattern[str]]]]] = {
    ESPPlatform.BRAZE: [
        ("output", re.compile(r"\{\{.+?\}\}")),
        ("logic", re.compile(r"\{%[^%]+%\}")),
    ],
    ESPPlatform.SFMC: [
        ("block", re.compile(r"%%\[[\s\S]*?\]%%")),
        ("output", re.compile(r"%%=[^%]+=%%")),
        ("output", re.compile(r"%%\w+%%")),
    ],
    ESPPlatform.ADOBE_CAMPAIGN: [
        ("output", re.compile(r"<%=[^%]+%>")),
        ("logic", re.compile(r"<%[^%=][^%]*%>")),
    ],
    ESPPlatform.KLAVIYO: [
        ("output", re.compile(r"\{\{[^}]+\}\}")),
        ("logic", re.compile(r"\{%[^%]+%\}")),
    ],
    ESPPlatform.MAILCHIMP: [
        ("output", re.compile(r"\*\|[^|]+\|\*")),
    ],
    ESPPlatform.HUBSPOT: [
        ("output", re.compile(r"\{\{[^}]+\}\}")),
        ("logic", re.compile(r"\{%[^%]+%\}")),
    ],
    ESPPlatform.ITERABLE: [
        ("output", re.compile(r"\{\{[^}]+\}\}")),
        ("output", re.compile(r"\[\[[^\]]+\]\]")),
    ],
}

# Variable name extractors per platform
_VAR_EXTRACTORS: Final[dict[ESPPlatform, re.Pattern[str]]] = {
    ESPPlatform.BRAZE: re.compile(r"\{\{\s*\$?\{?\s*(\w[\w.]*)\s*"),
    ESPPlatform.SFMC: re.compile(r"%%=?\[?\s*(?:v\(|@)?(\w[\w.]*)\s*"),
    ESPPlatform.ADOBE_CAMPAIGN: re.compile(r"<%=?\s*(\w[\w.]*)\s*"),
    ESPPlatform.KLAVIYO: re.compile(r"\{\{\s*(\w[\w.]*)\s*"),
    ESPPlatform.MAILCHIMP: re.compile(r"\*\|\s*(\w+)\s*\|\*"),
    ESPPlatform.HUBSPOT: re.compile(r"\{\{\s*(\w[\w.]*)\s*"),
    ESPPlatform.ITERABLE: re.compile(r"\{\{\s*(\w[\w.]*)\s*|\[\[\s*(\w[\w.]*)\s*"),
}


def _extract_variable_name(raw: str, platform: ESPPlatform) -> str:
    """Extract the variable/field name from a tag."""
    extractor = _VAR_EXTRACTORS.get(platform)
    if not extractor:
        return ""
    m = extractor.search(raw)
    if not m:
        return ""
    # Iterable has two groups ({{ }} and [[ ]])
    return m.group(1) or (m.group(2) if m.lastindex and m.lastindex >= 2 else "")


def _get_line_number(raw_html: str, pos: int) -> int:
    """Get approximate line number for a match position."""
    return raw_html[:pos].count("\n") + 1


def extract_tags(raw_html: str, platform: ESPPlatform) -> list[PersonalisationTag]:
    """Extract all personalisation tags for the detected platform."""
    patterns = _TAG_PATTERNS.get(platform)
    if not patterns:
        return []

    tags: list[PersonalisationTag] = []
    seen_spans: set[tuple[int, int]] = set()

    for tag_type, pattern in patterns:
        for m in pattern.finditer(raw_html):
            span = (m.start(), m.end())
            if span in seen_spans:
                continue
            seen_spans.add(span)
            raw = m.group(0)
            tags.append(
                PersonalisationTag(
                    platform=platform,
                    raw=raw,
                    tag_type=tag_type,
                    has_fallback=_has_fallback(raw, platform, raw_html),
                    line_number=_get_line_number(raw_html, m.start()),
                    variable_name=_extract_variable_name(raw, platform),
                )
            )

    return sorted(tags, key=lambda t: t.line_number)


# ---------------------------------------------------------------------------
# Fallback Detection
# ---------------------------------------------------------------------------

_FALLBACK_PATTERNS: Final[dict[ESPPlatform, re.Pattern[str]]] = {
    ESPPlatform.BRAZE: re.compile(r"\|\s*default\s*:"),
    ESPPlatform.SFMC: re.compile(r"IIF\s*\(\s*Empty\s*\(|IF\s+Empty\s*\(", re.IGNORECASE),
    ESPPlatform.ADOBE_CAMPAIGN: re.compile(r"\|\||[?]\s*.*\s*:"),
    ESPPlatform.KLAVIYO: re.compile(r"\|\s*default\s*:"),
    ESPPlatform.MAILCHIMP: re.compile(r"\*\|IF:[^|]+\|\*"),
    ESPPlatform.HUBSPOT: re.compile(r"\|\s*default\s*\("),
    ESPPlatform.ITERABLE: re.compile(r"defaultIfEmpty\b"),
}


def _has_fallback(tag: str, platform: ESPPlatform, raw_html: str = "") -> bool:
    """Check if a tag has a fallback/default value.

    For SFMC, also checks if the variable has an IF Empty() block elsewhere in the HTML.
    """
    pattern = _FALLBACK_PATTERNS.get(platform)
    if not pattern:
        return False
    if pattern.search(tag):
        return True
    # SFMC: check if an IF Empty() block exists for this variable anywhere in the HTML
    if platform == ESPPlatform.SFMC and raw_html:
        # Extract variable name from %%=v(@var)=%% or %%=@var=%% patterns
        var_match = re.search(r"v\((@\w+)\)", tag) or re.search(r"%%=?(@\w+)=?%%", tag)
        if var_match:
            var_name = re.escape(var_match.group(1))
            context_pattern = re.compile(rf"IF\s+Empty\s*\(\s*{var_name}\s*\)", re.IGNORECASE)
            return bool(context_pattern.search(raw_html))
    return False


_EMPTY_FALLBACK_PATTERNS: Final[dict[ESPPlatform, re.Pattern[str]]] = {
    ESPPlatform.BRAZE: re.compile(r"\|\s*default\s*:\s*['\"][\s]*['\"]"),
    ESPPlatform.KLAVIYO: re.compile(r"\|\s*default\s*:\s*['\"][\s]*['\"]"),
    ESPPlatform.HUBSPOT: re.compile(r"\|\s*default\s*\(\s*['\"][\s]*['\"]\s*\)"),
    ESPPlatform.ITERABLE: re.compile(r"defaultIfEmpty\s+\w+\s+['\"][\s]*['\"]"),
}


def _has_empty_fallback(tag: str, platform: ESPPlatform) -> bool:
    """Check if a fallback value is empty string."""
    pattern = _EMPTY_FALLBACK_PATTERNS.get(platform)
    if not pattern:
        return False
    return bool(pattern.search(tag))


# ---------------------------------------------------------------------------
# Delimiter Balance
# ---------------------------------------------------------------------------

_DELIMITER_PAIRS: Final[list[tuple[str, str, str]]] = [
    ("{{", "}}", "double curly braces"),
    ("{%", "%}", "template logic delimiters"),
    ("%%[", "]%%", "AMPscript block delimiters"),
    ("<%", "%>", "JSSP delimiters"),
    ("*|", "|*", "merge tag delimiters"),
    ("[[", "]]", "catalog delimiters"),
]


def check_delimiter_balance(raw_html: str, platform: ESPPlatform) -> list[str]:
    """Return list of unbalanced delimiter error descriptions."""
    errors: list[str] = []

    # Only check delimiters relevant to the platform
    relevant_pairs: list[tuple[str, str, str]] = []
    if platform in (
        ESPPlatform.BRAZE,
        ESPPlatform.KLAVIYO,
        ESPPlatform.HUBSPOT,
        ESPPlatform.UNKNOWN,
    ):
        relevant_pairs = [
            ("{{", "}}", "double curly braces"),
            ("{%", "%}", "template logic delimiters"),
        ]
    elif platform == ESPPlatform.SFMC:
        relevant_pairs = [("%%[", "]%%", "AMPscript block delimiters")]
    elif platform == ESPPlatform.ADOBE_CAMPAIGN:
        relevant_pairs = [("<%", "%>", "JSSP delimiters")]
    elif platform == ESPPlatform.MAILCHIMP:
        relevant_pairs = [("*|", "|*", "merge tag delimiters")]
    elif platform == ESPPlatform.ITERABLE:
        relevant_pairs = [
            ("{{", "}}", "double curly braces"),
            ("[[", "]]", "catalog delimiters"),
        ]

    for opener, closer, desc in relevant_pairs:
        open_count = raw_html.count(opener)
        close_count = raw_html.count(closer)
        if open_count != close_count:
            diff = abs(open_count - close_count)
            direction = "unclosed" if open_count > close_count else "extra closing"
            errors.append(f"{diff} {direction} {desc} ({opener}...{closer})")

    return errors


# ---------------------------------------------------------------------------
# Conditional Block Balance
# ---------------------------------------------------------------------------

_CONDITIONAL_PAIRS: Final[dict[ESPPlatform, list[tuple[re.Pattern[str], re.Pattern[str], str]]]] = {
    ESPPlatform.BRAZE: [
        (re.compile(r"\{%\s*if\b"), re.compile(r"\{%\s*endif\s*%\}"), "Liquid if/endif"),
        (re.compile(r"\{%\s*for\b"), re.compile(r"\{%\s*endfor\s*%\}"), "Liquid for/endfor"),
    ],
    ESPPlatform.KLAVIYO: [
        (re.compile(r"\{%\s*if\b"), re.compile(r"\{%\s*endif\s*%\}"), "Django if/endif"),
        (re.compile(r"\{%\s*for\b"), re.compile(r"\{%\s*endfor\s*%\}"), "Django for/endfor"),
    ],
    ESPPlatform.HUBSPOT: [
        (re.compile(r"\{%\s*if\b"), re.compile(r"\{%\s*endif\s*%\}"), "HubL if/endif"),
        (re.compile(r"\{%\s*for\b"), re.compile(r"\{%\s*endfor\s*%\}"), "HubL for/endfor"),
    ],
    ESPPlatform.SFMC: [
        (
            re.compile(r"\bIF\b", re.IGNORECASE),
            re.compile(r"\bENDIF\b", re.IGNORECASE),
            "AMPscript IF/ENDIF",
        ),
    ],
    ESPPlatform.ITERABLE: [
        (re.compile(r"\{\{#if\b"), re.compile(r"\{\{/if\}\}"), "Handlebars #if//if"),
        (re.compile(r"\{\{#each\b"), re.compile(r"\{\{/each\}\}"), "Handlebars #each//each"),
    ],
    ESPPlatform.MAILCHIMP: [
        (re.compile(r"\*\|IF:"), re.compile(r"\*\|END:IF\|\*"), "Merge IF/END:IF"),
    ],
}


def check_conditional_balance(raw_html: str, platform: ESPPlatform) -> list[str]:
    """Check conditional blocks are properly balanced."""
    errors: list[str] = []
    pairs = _CONDITIONAL_PAIRS.get(platform, [])

    for open_pat, close_pat, desc in pairs:
        open_count = len(open_pat.findall(raw_html))
        close_count = len(close_pat.findall(raw_html))
        if open_count != close_count:
            diff = abs(open_count - close_count)
            direction = "unclosed" if open_count > close_count else "extra closing"
            errors.append(f"{diff} {direction} {desc} block(s)")

    return errors


# ---------------------------------------------------------------------------
# Nesting Depth
# ---------------------------------------------------------------------------

_NESTING_OPENERS: Final[dict[ESPPlatform, re.Pattern[str]]] = {
    ESPPlatform.BRAZE: re.compile(r"\{%\s*if\b"),
    ESPPlatform.KLAVIYO: re.compile(r"\{%\s*if\b"),
    ESPPlatform.HUBSPOT: re.compile(r"\{%\s*if\b"),
    ESPPlatform.SFMC: re.compile(r"\bIF\b(?!\s*Empty)", re.IGNORECASE),
    ESPPlatform.ITERABLE: re.compile(r"\{\{#if\b"),
    ESPPlatform.MAILCHIMP: re.compile(r"\*\|IF:"),
}

_NESTING_CLOSERS: Final[dict[ESPPlatform, re.Pattern[str]]] = {
    ESPPlatform.BRAZE: re.compile(r"\{%\s*endif\s*%\}"),
    ESPPlatform.KLAVIYO: re.compile(r"\{%\s*endif\s*%\}"),
    ESPPlatform.HUBSPOT: re.compile(r"\{%\s*endif\s*%\}"),
    ESPPlatform.SFMC: re.compile(r"\bENDIF\b", re.IGNORECASE),
    ESPPlatform.ITERABLE: re.compile(r"\{\{/if\}\}"),
    ESPPlatform.MAILCHIMP: re.compile(r"\*\|END:IF\|\*"),
}


def check_nesting_depth(raw_html: str, platform: ESPPlatform, max_depth: int = 3) -> list[str]:
    """Flag conditional nesting exceeding max_depth levels."""
    opener_pat = _NESTING_OPENERS.get(platform)
    closer_pat = _NESTING_CLOSERS.get(platform)
    if not opener_pat or not closer_pat:
        return []

    # Build a list of (position, type) events
    events: list[tuple[int, str]] = []
    for m in opener_pat.finditer(raw_html):
        events.append((m.start(), "open"))
    for m in closer_pat.finditer(raw_html):
        events.append((m.start(), "close"))
    events.sort(key=lambda e: e[0])

    violations: list[str] = []
    depth = 0
    for pos, event_type in events:
        if event_type == "open":
            depth += 1
            if depth > max_depth:
                line = _get_line_number(raw_html, pos)
                violations.append(
                    f"Conditional nesting depth {depth} exceeds max {max_depth} at line {line}"
                )
        else:
            depth = max(0, depth - 1)

    return violations


# ---------------------------------------------------------------------------
# Syntax Validation
# ---------------------------------------------------------------------------


def validate_liquid_syntax(raw_html: str) -> list[str]:
    """Validate Liquid syntax for Braze/Klaviyo."""
    errors: list[str] = []
    # Check for common liquid errors: unclosed filters, bad filter chains
    for m in re.finditer(r"\{\{(.+?)\}\}", raw_html):
        content = m.group(1).strip()
        # Empty tag
        if not content:
            line = _get_line_number(raw_html, m.start())
            errors.append(f"Empty Liquid output tag at line {line}")
            continue
        # Dangling pipe at end
        if content.rstrip().endswith("|"):
            line = _get_line_number(raw_html, m.start())
            errors.append(f"Dangling filter pipe in Liquid tag at line {line}")
    return errors


def validate_ampscript_syntax(raw_html: str) -> list[str]:
    """Validate AMPscript syntax for SFMC."""
    errors: list[str] = []
    # Check SET without @ prefix
    for m in re.finditer(r"SET\s+(\w+)\s*=", raw_html, re.IGNORECASE):
        var_name = m.group(1)
        if not var_name.startswith("@"):
            line = _get_line_number(raw_html, m.start())
            errors.append(f"AMPscript SET variable '{var_name}' missing @ prefix at line {line}")
    # Check unclosed function calls within %%[...]%%
    for m in re.finditer(r"%%\[([\s\S]*?)\]%%", raw_html):
        block = m.group(1)
        open_parens = block.count("(")
        close_parens = block.count(")")
        if open_parens != close_parens:
            line = _get_line_number(raw_html, m.start())
            errors.append(f"Unbalanced parentheses in AMPscript block at line {line}")
    return errors


def validate_jssp_syntax(raw_html: str) -> list[str]:
    """Validate JSSP/EL syntax for Adobe Campaign."""
    errors: list[str] = []
    # Check for unclosed code blocks
    for m in re.finditer(r"<%([^%=][^%]*?)%>", raw_html):
        content = m.group(1).strip()
        if content and ("\n" in content or ";" in content):
            # Multi-statement block — last statement should end with ;
            stmts = [s.strip() for s in content.split(";") if s.strip()]
            for stmt in stmts:
                open_parens = stmt.count("(")
                close_parens = stmt.count(")")
                if open_parens != close_parens:
                    line = _get_line_number(raw_html, m.start())
                    errors.append(f"Unbalanced parentheses in JSSP block at line {line}")
                    break
    return errors


def validate_other_syntax(raw_html: str, platform: ESPPlatform) -> list[str]:
    """Validate syntax for Mailchimp/HubSpot/Iterable."""
    errors: list[str] = []
    if platform == ESPPlatform.MAILCHIMP:
        # Check for malformed merge tags (missing closing)
        for m in re.finditer(r"\*\|([^|]*?)(?:\|\*|$)", raw_html):
            content = m.group(1).strip()
            if not content:
                line = _get_line_number(raw_html, m.start())
                errors.append(f"Empty merge tag at line {line}")
    elif platform == ESPPlatform.HUBSPOT:
        # Check for empty output tags
        for m in re.finditer(r"\{\{\s*\}\}", raw_html):
            line = _get_line_number(raw_html, m.start())
            errors.append(f"Empty HubL output tag at line {line}")
    elif platform == ESPPlatform.ITERABLE:
        # Check for unclosed Handlebars helpers
        for m in re.finditer(r"\{\{#(\w+)\b", raw_html):
            helper = m.group(1)
            closer = f"{{{{/{helper}}}}}"
            if closer not in raw_html:
                line = _get_line_number(raw_html, m.start())
                errors.append(f"Unclosed Handlebars helper '{{{{#{helper}}}}}' at line {line}")
    return errors


# ---------------------------------------------------------------------------
# Main Analysis (Cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=32)
def analyze_personalisation(raw_html: str) -> PersonalisationAnalysis:
    """Full personalisation analysis with caching."""
    primary_platform, _confidence = detect_platform(raw_html)
    all_platforms = detect_all_platforms(raw_html)

    # If no personalisation detected
    if primary_platform == ESPPlatform.UNKNOWN and _confidence == 0.0:
        return PersonalisationAnalysis(
            detected_platforms=[],
            primary_platform=ESPPlatform.UNKNOWN,
            tags=[],
            total_tags=0,
            tags_with_fallback=0,
            tags_without_fallback=0,
            unbalanced_delimiters=[],
            unbalanced_conditionals=[],
            nested_depth_violations=[],
            is_mixed_platform=False,
            has_personalisation=False,
        )

    tags = extract_tags(raw_html, primary_platform)
    output_tags = [t for t in tags if t.tag_type == "output"]
    with_fallback = sum(1 for t in output_tags if t.has_fallback)
    without_fallback = len(output_tags) - with_fallback

    delimiter_errors = check_delimiter_balance(raw_html, primary_platform)
    conditional_errors = check_conditional_balance(raw_html, primary_platform)
    nesting_violations = check_nesting_depth(raw_html, primary_platform)

    # Syntax validation
    syntax_errors: list[str] = []
    if primary_platform in (ESPPlatform.BRAZE, ESPPlatform.KLAVIYO):
        syntax_errors = validate_liquid_syntax(raw_html)
    elif primary_platform == ESPPlatform.SFMC:
        syntax_errors = validate_ampscript_syntax(raw_html)
    elif primary_platform == ESPPlatform.ADOBE_CAMPAIGN:
        syntax_errors = validate_jssp_syntax(raw_html)
    elif primary_platform in (ESPPlatform.MAILCHIMP, ESPPlatform.HUBSPOT, ESPPlatform.ITERABLE):
        syntax_errors = validate_other_syntax(raw_html, primary_platform)

    # Empty fallback detection
    empty_fallbacks: list[str] = []
    for t in output_tags:
        if t.has_fallback and _has_empty_fallback(t.raw, primary_platform):
            empty_fallbacks.append(
                f"Empty fallback for '{t.variable_name}' at line {t.line_number}"
            )

    return PersonalisationAnalysis(
        detected_platforms=all_platforms or [primary_platform],
        primary_platform=primary_platform,
        tags=tags,
        total_tags=len(tags),
        tags_with_fallback=with_fallback,
        tags_without_fallback=without_fallback,
        unbalanced_delimiters=delimiter_errors,
        unbalanced_conditionals=conditional_errors,
        nested_depth_violations=nesting_violations,
        is_mixed_platform=len(all_platforms) > 1,
        has_personalisation=True,
        syntax_errors=syntax_errors,
        empty_fallbacks=empty_fallbacks,
    )


def clear_personalisation_cache() -> None:
    """Clear the analysis cache (useful between test runs)."""
    analyze_personalisation.cache_clear()
