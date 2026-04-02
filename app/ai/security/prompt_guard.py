"""Prompt injection detection for AI agent inputs.

Scans text inputs for patterns that attempt to override agent instructions.
Supports three modes: warn (log only), strip (remove flagged segments), block (raise error).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class InjectionScanResult:
    """Result of a prompt injection scan."""

    clean: bool
    flags: list[str] = field(default_factory=lambda: [])  # noqa: PIE807 — `list` triggers pyright reportUnknownVariableType
    sanitized: str | None = None


# ── Compiled pattern categories ──────────────────────────────────────
# Each entry: (flag_name, compiled_regex)
# Patterns are case-insensitive and use bounded quantifiers to avoid ReDoS.

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Instruction override attempts
    (
        "instruction_override",
        re.compile(
            r"(?:"
            r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions"
            r"|disregard\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|rules|guidelines)"
            r"|forget\s+(?:all\s+)?(?:your|previous|prior)\s+instructions"
            r"|override\s+(?:all\s+)?(?:previous|prior|system)\s+(?:instructions|rules|prompts)"
            r"|do\s+not\s+follow\s+(?:your|the|any)\s+(?:previous|prior|original)\s+instructions"
            r")",
            re.IGNORECASE,
        ),
    ),
    # System prompt leak attempts
    (
        "system_prompt_leak",
        re.compile(
            r"(?:"
            r"(?:output|reveal|show|display|print|repeat|echo)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions|rules)"
            r"|what\s+(?:are|is)\s+your\s+(?:system\s+)?(?:prompt|instructions|rules)"
            r"|(?:system|original|initial)\s+prompt\s+(?:verbatim|exactly|word\s+for\s+word)"
            r")",
            re.IGNORECASE,
        ),
    ),
    # Role-play / persona hijack
    (
        "roleplay_attempt",
        re.compile(
            r"(?:"
            r"you\s+are\s+now\s+(?:a|an|the)\b"
            r"|from\s+now\s+on\s+you\s+(?:are|will|should|must)\b"
            r"|pretend\s+(?:to\s+be|you\s+are)\b"
            r"|act\s+as\s+(?:a|an|if\s+you\s+(?:are|were))\b"
            r"|i\s+want\s+you\s+to\s+(?:act|behave|pretend|role.?play)\b"
            r")",
            re.IGNORECASE,
        ),
    ),
    # Delimiter / context boundary attacks
    (
        "delimiter_attack",
        re.compile(
            r"(?:"
            r"(?:^|\n)(?:---\s*\n){3,}"  # 3+ consecutive --- lines
            r"|(?:^|\n)(?:###\s*\n){3,}"  # 3+ consecutive ### lines
            r"|(?:^|\n)(?:===\s*\n){3,}"  # 3+ consecutive === lines
            r"|<\/?(?:system|instructions|prompt|context|rules)>"  # XML-like injection tags
            r")",
            re.IGNORECASE,
        ),
    ),
    # Context switch attempts
    (
        "context_switch",
        re.compile(
            r"(?:"
            r"(?:^|\n)\s*(?:SYSTEM|System)\s*:"  # SYSTEM: prefix
            r"|(?:^|\n)\s*Human\s*:"  # Human: prefix
            r"|(?:^|\n)\s*Assistant\s*:"  # Assistant: prefix
            r"|(?:^|\n)\s*NEW\s+CONVERSATION\b"  # NEW CONVERSATION marker
            r"|(?:^|\n)\s*\[(?:SYSTEM|INST|SYS)\]"  # [SYSTEM] / [INST] / [SYS] markers
            r")",
            re.IGNORECASE,
        ),
    ),
]


def scan_for_injection(text: str, *, mode: str = "warn") -> InjectionScanResult:
    """Scan text for prompt injection patterns.

    Args:
        text: The text to scan.
        mode: Detection mode — "warn" (log only), "strip" (remove flagged),
              or "block" (raise error).

    Returns:
        InjectionScanResult with clean status, flags, and optional sanitized text.

    Raises:
        PromptInjectionError: If mode is "block" and injection is detected.
    """
    if not text:
        return InjectionScanResult(clean=True)

    flags: list[str] = []
    matches: list[tuple[str, re.Match[str]]] = []

    for flag_name, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            if flag_name not in flags:
                flags.append(flag_name)
            matches.append((flag_name, m))

    if not flags:
        return InjectionScanResult(clean=True)

    logger.warning(
        "security.prompt_injection_detected",
        flags=flags,
        mode=mode,
        text_length=len(text),
        match_count=len(matches),
    )

    if mode == "block":
        from app.core.exceptions import PromptInjectionError

        raise PromptInjectionError(flags=flags)

    sanitized: str | None = None
    if mode == "strip":
        sanitized = _strip_matches(text, matches)

    return InjectionScanResult(clean=False, flags=flags, sanitized=sanitized)


def scan_fields(
    fields: Mapping[str, str | None], *, mode: str = "warn"
) -> dict[str, InjectionScanResult]:
    """Scan multiple named fields for prompt injection.

    Args:
        fields: Mapping of field_name → text (None values are skipped).
        mode: Detection mode.

    Returns:
        Dict of field_name → InjectionScanResult for non-None fields.
    """
    results: dict[str, InjectionScanResult] = {}
    for name, value in fields.items():
        if value is not None:
            results[name] = scan_for_injection(value, mode=mode)
    return results


def _strip_matches(text: str, matches: list[tuple[str, re.Match[str]]]) -> str:
    """Remove matched segments from text, preserving surrounding content."""
    if not matches:
        return text

    # Sort matches by start position, remove overlapping spans
    spans = sorted([(m.start(), m.end()) for _, m in matches])
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Build result by keeping non-matched segments
    parts: list[str] = []
    pos = 0
    for start, end in merged:
        parts.append(text[pos:start])
        pos = end
    parts.append(text[pos:])

    return "".join(parts).strip()
