"""Input sanitization and output validation for AI requests.

Strips PII patterns from prompts before sending to external APIs.
Validates AI responses before returning to clients.
"""

import re

from app.core.logging import get_logger

logger = get_logger(__name__)

# PII patterns to strip from prompts
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.IGNORECASE)),
    (
        "phone_intl",
        re.compile(r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"),
    ),
    ("phone_us", re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
]

# Maximum response content length (safety check)
_MAX_RESPONSE_LENGTH = 100_000


def sanitize_prompt(text: str) -> str:
    """Strip PII patterns from a prompt string.

    Replaces detected PII with placeholder tokens (e.g., [EMAIL], [PHONE_INTL]).

    Args:
        text: Raw prompt text.

    Returns:
        Sanitized text with PII patterns replaced.
    """
    sanitized = text
    replacements = 0

    for label, pattern in _PII_PATTERNS:
        placeholder = f"[{label.upper()}]"
        new_text, count = pattern.subn(placeholder, sanitized)
        if count > 0:
            sanitized = new_text
            replacements += count

    if replacements > 0:
        logger.info(
            "ai.sanitize.pii_stripped",
            replacement_count=replacements,
        )

    return sanitized


def validate_output(content: str) -> str:
    """Validate and clean AI response content.

    Checks:
    - Strips null bytes
    - Truncates excessively long responses

    Args:
        content: Raw AI response content.

    Returns:
        Validated content string.
    """
    # Strip null bytes
    content = content.replace("\x00", "")

    # Truncate excessively long responses
    if len(content) > _MAX_RESPONSE_LENGTH:
        logger.warning(
            "ai.validate.response_truncated",
            original_length=len(content),
            max_length=_MAX_RESPONSE_LENGTH,
        )
        content = content[:_MAX_RESPONSE_LENGTH]

    return content
