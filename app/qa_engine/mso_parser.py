"""MSO conditional comment parser and validator.

Provides validate_mso_conditionals() for use by:
- QA fallback check (via rule engine custom functions)
- Outlook Fixer agent (direct import for post-generation validation)

All parsing operates on raw HTML strings because lxml strips HTML comments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class MSOIssue:
    """A single MSO validation issue with location context."""

    category: str  # balanced_pair | vml_orphan | namespace | ghost_table | syntax
    message: str
    severity: str = "warning"  # error | warning | info
    position: int = -1  # Approximate char offset in raw HTML (-1 = unknown)


@dataclass
class MSOValidationResult:
    """Aggregate result of MSO conditional validation."""

    issues: list[MSOIssue] = field(default_factory=lambda: list[MSOIssue]())
    opener_count: int = 0
    closer_count: int = 0
    vml_element_count: int = 0
    has_vml_namespace: bool = False
    has_office_namespace: bool = False

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0


# ---------------------------------------------------------------------------
# Regex patterns (compiled once)
# ---------------------------------------------------------------------------

# MSO conditional openers: <!--[if mso]>, <!--[if gte mso 12]>, etc.
_MSO_OPENER_RE = re.compile(r"<!--\[if\s+([^\]]+)\]>", re.IGNORECASE)
# Standard MSO closer
_MSO_CLOSER_RE = re.compile(r"<!\[endif\]-->")
# Non-MSO opener: <!--[if !mso]><!-->
_NON_MSO_OPENER_RE = re.compile(r"<!--\[if\s+!mso\]><!--\s*>", re.IGNORECASE)
# Non-MSO closer: <!--<![endif]-->
_NON_MSO_CLOSER_RE = re.compile(r"<!--<!\[endif\]-->")

# Valid MSO conditional expressions
_VALID_CONDITION_RE = re.compile(
    r"^(?:"
    r"mso"  # plain mso
    r"|!mso(?:\]><!--\s*>)?"  # !mso or !mso]><!-->
    r"|(?:gte|gt|lte|lt)\s+mso\s+\d+"  # operator mso version
    r"|mso\s+\d+"  # mso version
    r"|mso\s*\|\s*IE"  # mso | IE
    r")$",
    re.IGNORECASE,
)

# Valid Outlook version numbers
_VALID_VERSIONS = frozenset({9, 10, 11, 12, 14, 15, 16})

# VML elements
_VML_ELEMENTS_RE = re.compile(
    r"<(?:v:(?:rect|roundrect|oval|line|shape|image|group|polyline|arc|curve"
    r"|fill|stroke|shadow|textbox|imagedata|path|formulas)"
    r"|o:(?:OfficeDocumentSettings|AllowPNG|PixelsPerInch|lock)"
    r"|w:anchorlock)\b",
    re.IGNORECASE,
)

# Namespace declarations on <html> tag
_XMLNS_V_RE = re.compile(r'xmlns:v\s*=\s*["\']urn:schemas-microsoft-com:vml["\']', re.IGNORECASE)
_XMLNS_O_RE = re.compile(
    r'xmlns:o\s*=\s*["\']urn:schemas-microsoft-com:office:office["\']', re.IGNORECASE
)

# Ghost table pattern — table inside MSO conditional
_GHOST_TABLE_RE = re.compile(r"<table\b[^>]*>", re.IGNORECASE)
_WIDTH_ATTR_RE = re.compile(r'\bwidth\s*=\s*["\']?\d+', re.IGNORECASE)
_MAX_WIDTH_DIV_RE = re.compile(r"max-width\s*:", re.IGNORECASE)

# Version number in condition
_VERSION_RE = re.compile(r"mso\s+(\d+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Sub-validators
# ---------------------------------------------------------------------------


def _get_mso_openers(html: str) -> list[tuple[int, str]]:
    """Find all MSO conditional openers (excluding !mso) as (position, condition)."""
    openers: list[tuple[int, str]] = []
    for m in _MSO_OPENER_RE.finditer(html):
        condition = m.group(1).strip()
        if not condition.lower().startswith("!mso"):
            openers.append((m.start(), condition))
    return openers


def _get_mso_closer_positions(html: str) -> list[int]:
    """Find positions of MSO closers, excluding non-MSO closers.

    Non-MSO closer ``<!--<![endif]-->`` contains ``<![endif]-->`` at offset +4.
    We exclude those from the regular closer list.
    """
    non_mso_closer_positions = {m.start() for m in _NON_MSO_CLOSER_RE.finditer(html)}
    return [
        m.start()
        for m in _MSO_CLOSER_RE.finditer(html)
        if (m.start() - 4) not in non_mso_closer_positions
    ]


def _find_mso_blocks(html: str) -> list[tuple[int, int, str]]:
    """Find all MSO conditional blocks as (opener_pos, closer_pos, condition).

    Returns matched pairs. Unmatched openers/closers tracked separately.
    """
    blocks: list[tuple[int, int, str]] = []
    openers = _get_mso_openers(html)
    closers = _get_mso_closer_positions(html)

    # Match openers to closers (nearest unmatched closer after opener)
    used_closers: set[int] = set()
    for opener_pos, condition in openers:
        for closer_pos in closers:
            if closer_pos > opener_pos and closer_pos not in used_closers:
                used_closers.add(closer_pos)
                blocks.append((opener_pos, closer_pos, condition))
                break

    return blocks


def _validate_balanced_pairs(html: str) -> tuple[list[MSOIssue], int, int]:
    """Validate MSO conditional opener/closer balance."""
    issues: list[MSOIssue] = []

    mso_openers = _get_mso_openers(html)
    mso_closer_positions = _get_mso_closer_positions(html)

    # Non-MSO blocks
    non_mso_openers = list(_NON_MSO_OPENER_RE.finditer(html))
    non_mso_closers = list(_NON_MSO_CLOSER_RE.finditer(html))

    # Check MSO balance
    opener_count = len(mso_openers)
    closer_count = len(mso_closer_positions)

    if opener_count > closer_count:
        diff = opener_count - closer_count
        issues.append(
            MSOIssue(
                category="balanced_pair",
                message=f"{diff} MSO conditional opener(s) without matching closer",
                severity="error",
            )
        )
    elif closer_count > opener_count:
        diff = closer_count - opener_count
        issues.append(
            MSOIssue(
                category="balanced_pair",
                message=f"{diff} MSO conditional closer(s) without matching opener",
                severity="error",
            )
        )

    # Check non-MSO balance
    if len(non_mso_openers) > len(non_mso_closers):
        diff = len(non_mso_openers) - len(non_mso_closers)
        issues.append(
            MSOIssue(
                category="balanced_pair",
                message=f"{diff} non-MSO conditional opener(s) without matching <!--<![endif]-->",
                severity="error",
            )
        )
    elif len(non_mso_closers) > len(non_mso_openers):
        diff = len(non_mso_closers) - len(non_mso_openers)
        issues.append(
            MSOIssue(
                category="balanced_pair",
                message=f"{diff} non-MSO conditional closer(s) without matching opener",
                severity="error",
            )
        )

    return issues, opener_count, closer_count


def _validate_conditional_syntax(html: str) -> list[MSOIssue]:
    """Validate each MSO conditional expression for valid syntax."""
    issues: list[MSOIssue] = []

    for m in _MSO_OPENER_RE.finditer(html):
        condition = m.group(1).strip()
        # Skip non-MSO
        if condition.lower().startswith("!mso"):
            continue

        # Check basic syntax
        if not _VALID_CONDITION_RE.match(condition):
            issues.append(
                MSOIssue(
                    category="syntax",
                    message=f"Invalid MSO conditional syntax: <!--[if {condition}]>",
                    severity="warning",
                    position=m.start(),
                )
            )
            continue

        # Check version number validity
        version_match = _VERSION_RE.search(condition)
        if version_match:
            version = int(version_match.group(1))
            if version not in _VALID_VERSIONS:
                issues.append(
                    MSOIssue(
                        category="syntax",
                        message=f"Invalid Outlook version {version} in <!--[if {condition}]> — valid: {sorted(_VALID_VERSIONS)}",
                        severity="warning",
                        position=m.start(),
                    )
                )

    return issues


def _validate_vml_nesting(html: str) -> tuple[list[MSOIssue], int]:
    """Verify VML/Office elements are inside MSO conditional blocks."""
    issues: list[MSOIssue] = []
    blocks = _find_mso_blocks(html)

    vml_matches = list(_VML_ELEMENTS_RE.finditer(html))
    vml_count = len(vml_matches)

    for m in vml_matches:
        pos = m.start()
        inside = False
        for opener_pos, closer_pos, _ in blocks:
            if opener_pos < pos < closer_pos:
                inside = True
                break
        if not inside:
            element = m.group(0)
            issues.append(
                MSOIssue(
                    category="vml_orphan",
                    message=f"VML/Office element {element} outside MSO conditional block",
                    severity="warning",
                    position=pos,
                )
            )

    return issues, vml_count


def _validate_namespaces(html: str, has_vml: bool) -> tuple[list[MSOIssue], bool, bool]:
    """Check namespace declarations on <html> tag when VML/Office elements exist."""
    issues: list[MSOIssue] = []

    # Extract <html> tag
    html_tag_match = re.search(r"<html\b[^>]*>", html, re.IGNORECASE)
    html_tag = html_tag_match.group(0) if html_tag_match else ""

    has_xmlns_v = bool(_XMLNS_V_RE.search(html_tag))
    has_xmlns_o = bool(_XMLNS_O_RE.search(html_tag))

    if has_vml:
        if not has_xmlns_v:
            issues.append(
                MSOIssue(
                    category="namespace",
                    message="VML elements present but missing xmlns:v on <html> tag",
                    severity="warning",
                )
            )
        if not has_xmlns_o:
            issues.append(
                MSOIssue(
                    category="namespace",
                    message="VML/Office elements present but missing xmlns:o on <html> tag",
                    severity="warning",
                )
            )

    return issues, has_xmlns_v, has_xmlns_o


def _validate_ghost_tables(html: str) -> list[MSOIssue]:
    """Validate ghost table structure in MSO conditional blocks."""
    issues: list[MSOIssue] = []
    blocks = _find_mso_blocks(html)

    for opener_pos, closer_pos, _ in blocks:
        block_content = html[opener_pos:closer_pos]

        # Find tables in this block
        for table_match in _GHOST_TABLE_RE.finditer(block_content):
            table_tag = table_match.group(0)
            table_abs_pos = opener_pos + table_match.start()

            # Only flag as ghost table if there's a max-width div nearby
            context_start = max(0, table_abs_pos - 500)
            context_end = min(len(html), table_abs_pos + 500)
            context = html[context_start:context_end]

            if not _MAX_WIDTH_DIV_RE.search(context):
                continue

            # Check width attribute
            if not _WIDTH_ATTR_RE.search(table_tag):
                issues.append(
                    MSOIssue(
                        category="ghost_table",
                        message="MSO ghost table missing width attribute — Outlook needs explicit widths",
                        severity="warning",
                        position=table_abs_pos,
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_mso_conditionals(html: str) -> MSOValidationResult:
    """Validate MSO conditional comments, VML nesting, and namespace declarations.

    This is the public API used by:
    - QA fallback check (via custom check functions)
    - Outlook Fixer agent (direct import for post-generation validation)
    """
    result = MSOValidationResult()

    if not html or not html.strip():
        return result

    # 1. Balanced pairs
    pair_issues, opener_count, closer_count = _validate_balanced_pairs(html)
    result.issues.extend(pair_issues)
    result.opener_count = opener_count
    result.closer_count = closer_count

    # 2. Conditional syntax
    syntax_issues = _validate_conditional_syntax(html)
    result.issues.extend(syntax_issues)

    # 3. VML nesting
    vml_issues, vml_count = _validate_vml_nesting(html)
    result.issues.extend(vml_issues)
    result.vml_element_count = vml_count

    # 4. Namespace declarations
    has_vml = vml_count > 0
    ns_issues, has_xmlns_v, has_xmlns_o = _validate_namespaces(html, has_vml)
    result.issues.extend(ns_issues)
    result.has_vml_namespace = has_xmlns_v
    result.has_office_namespace = has_xmlns_o

    # 5. Ghost tables
    ghost_issues = _validate_ghost_tables(html)
    result.issues.extend(ghost_issues)

    logger.debug(
        "mso_parser.validation_complete",
        issues=len(result.issues),
        openers=result.opener_count,
        closers=result.closer_count,
        vml_elements=result.vml_element_count,
    )

    return result


# ---------------------------------------------------------------------------
# Caching layer for QA check integration
# ---------------------------------------------------------------------------

_mso_cache: dict[str, MSOValidationResult] = {}


def get_cached_result(raw_html: str) -> MSOValidationResult:
    """Get cached MSO validation result, computing if not cached.

    Used by custom check functions to avoid re-parsing the same HTML
    across multiple rule evaluations within a single check run.
    Cache is cleared at the start of each FallbackCheck.run() call,
    so it holds at most one entry per run.
    """
    if raw_html not in _mso_cache:
        _mso_cache[raw_html] = validate_mso_conditionals(raw_html)
    return _mso_cache[raw_html]


def clear_mso_cache() -> None:
    """Clear the MSO validation cache. Called at the start of each check run."""
    _mso_cache.clear()
