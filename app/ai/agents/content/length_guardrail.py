"""Deterministic length guardrails for Content agent output.

Post-generation validation: checks character/word counts per operation
type and cleans up excessive punctuation. Returns structured warnings
for retry decisions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Per-operation length limits ──


@dataclass(frozen=True)
class LengthLimit:
    """Length constraint for a content operation."""

    min_chars: int | None = None
    max_chars: int | None = None
    min_words: int | None = None
    max_words: int | None = None
    # For relative operations (rewrite/shorten/expand/tone_adjust)
    min_ratio: float | None = None  # min output/input ratio
    max_ratio: float | None = None  # max output/input ratio


OPERATION_LIMITS: dict[str, LengthLimit] = {
    "subject_line": LengthLimit(min_chars=10, max_chars=60),
    "preheader": LengthLimit(min_chars=40, max_chars=100),
    "cta": LengthLimit(min_words=2, max_words=5),
    "body_copy": LengthLimit(min_chars=20),  # no hard max — varies by brief
    "rewrite": LengthLimit(min_ratio=0.8, max_ratio=1.2),
    "shorten": LengthLimit(min_ratio=0.5, max_ratio=0.7),
    "expand": LengthLimit(min_ratio=1.2, max_ratio=1.5),
    "tone_adjust": LengthLimit(min_ratio=0.8, max_ratio=1.2),
}

# ── Punctuation cleanup patterns ──

_EXCESSIVE_EXCLAMATION = re.compile(r"!{2,}")
_EXCESSIVE_QUESTION = re.compile(r"\?{2,}")
_EXCESSIVE_ELLIPSIS = re.compile(r"\.{3,}")


@dataclass(frozen=True)
class LengthCheckResult:
    """Result of length validation for a single alternative."""

    text: str
    operation: str
    char_count: int
    word_count: int
    warnings: tuple[str, ...]
    passed: bool


def clean_punctuation(text: str) -> str:
    """Strip excessive punctuation from generated copy.

    !!! → !
    ??? → ?
    ... → …
    """
    text = _EXCESSIVE_EXCLAMATION.sub("!", text)
    text = _EXCESSIVE_QUESTION.sub("?", text)
    text = _EXCESSIVE_ELLIPSIS.sub("\u2026", text)
    return text


def validate_length(
    text: str,
    operation: str,
    original_text: str | None = None,
) -> LengthCheckResult:
    """Validate a single text alternative against operation-specific limits.

    Args:
        text: Generated text to validate.
        operation: Content operation type.
        original_text: Source text (needed for ratio-based operations).

    Returns:
        LengthCheckResult with warnings and pass/fail status.
    """
    limits = OPERATION_LIMITS.get(operation)
    if limits is None:
        return LengthCheckResult(
            text=text,
            operation=operation,
            char_count=len(text),
            word_count=len(text.split()),
            warnings=(),
            passed=True,
        )

    char_count = len(text)
    word_count = len(text.split())
    warnings: list[str] = []

    # Absolute character limits
    if limits.max_chars is not None and char_count > limits.max_chars:
        warnings.append(f"{operation}: {char_count} chars exceeds max {limits.max_chars}")
    if limits.min_chars is not None and char_count < limits.min_chars:
        warnings.append(f"{operation}: {char_count} chars below min {limits.min_chars}")

    # Absolute word limits
    if limits.max_words is not None and word_count > limits.max_words:
        warnings.append(f"{operation}: {word_count} words exceeds max {limits.max_words}")
    if limits.min_words is not None and word_count < limits.min_words:
        warnings.append(f"{operation}: {word_count} words below min {limits.min_words}")

    # Ratio-based limits (need original text)
    if original_text:
        ratio = char_count / len(original_text)
        if limits.max_ratio is not None and ratio > limits.max_ratio:
            pct = int(ratio * 100)
            max_pct = int(limits.max_ratio * 100)
            warnings.append(f"{operation}: output is {pct}% of original, max allowed {max_pct}%")
        if limits.min_ratio is not None and ratio < limits.min_ratio:
            pct = int(ratio * 100)
            min_pct = int(limits.min_ratio * 100)
            warnings.append(f"{operation}: output is {pct}% of original, min allowed {min_pct}%")

    return LengthCheckResult(
        text=text,
        operation=operation,
        char_count=char_count,
        word_count=word_count,
        warnings=tuple(warnings),
        passed=len(warnings) == 0,
    )


def validate_alternatives(
    alternatives: list[str],
    operation: str,
    original_text: str | None = None,
) -> tuple[list[str], list[str]]:
    """Validate all alternatives and collect warnings.

    Also applies punctuation cleanup to every alternative.

    Args:
        alternatives: Generated text alternatives.
        operation: Content operation type.
        original_text: Source text for ratio-based operations.

    Returns:
        Tuple of (cleaned_alternatives, all_warnings).
    """
    cleaned: list[str] = []
    all_warnings: list[str] = []

    for alt in alternatives:
        alt = clean_punctuation(alt)
        cleaned.append(alt)

        result = validate_length(alt, operation, original_text)
        all_warnings.extend(result.warnings)

    return cleaned, all_warnings


def build_retry_constraint(operation: str, warnings: list[str]) -> str | None:
    """Build a retry instruction from length warnings.

    Returns a prompt fragment to inject on retry, or None if no retry needed.
    Only retries for max violations (too long/too many words) — min violations
    are warnings only (the LLM can't meaningfully "make it longer" without
    losing quality).
    """
    limits = OPERATION_LIMITS.get(operation)
    if limits is None:
        return None

    # Only retry for "too long" / "too many" violations
    retry_parts: list[str] = []

    for w in warnings:
        if "exceeds max" in w:
            if limits.max_chars is not None and "chars exceeds" in w:
                retry_parts.append(
                    f"CRITICAL: Keep the {operation} under {limits.max_chars} characters."
                )
            if limits.max_words is not None and "words exceeds" in w:
                retry_parts.append(
                    f"CRITICAL: Keep the {operation} to {limits.max_words} words maximum."
                )
        if "max allowed" in w and limits.max_ratio is not None:
            max_pct = int(limits.max_ratio * 100)
            retry_parts.append(
                f"CRITICAL: Output must not exceed {max_pct}% of the original text length."
            )

    if not retry_parts:
        return None

    return " ".join(dict.fromkeys(retry_parts))  # deduplicate
