# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
"""PII redaction for logs and eval traces.

Regex-based redactor that replaces email addresses, phone numbers, SSNs, and
credit card numbers with placeholder tokens.  Used by the structlog processor
chain and eval trace writers to prevent PII from reaching observability systems.

Patterns are intentionally duplicated from ``app.ai.sanitize`` to maintain
layer separation (core must not import ai).
"""

from __future__ import annotations

import re

from structlog.typing import EventDict, WrappedLogger

# ---------------------------------------------------------------------------
# Compiled PII patterns (module-level — zero cost after first import)
# ---------------------------------------------------------------------------

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.IGNORECASE)),
    (
        "PHONE_INTL",
        re.compile(r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"),
    ),
    ("PHONE", re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "CREDIT_CARD",
        re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    ),
]

_SKIP_KEYS = frozenset({"timestamp", "level", "request_id", "logger"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def redact_pii(text: str) -> str:
    """Replace PII patterns in *text* with placeholder tokens.

    >>> redact_pii("user@example.com")
    '[EMAIL]'
    """
    for label, pattern in _PII_PATTERNS:
        text = pattern.sub(f"[{label}]", text)
    return text


def redact_value(value: object) -> object:
    """Recursively redact PII from an arbitrary value.

    Handles ``str``, ``dict``, and ``list`` — all other types pass through
    unchanged.  Designed for eval trace dicts before JSON serialisation.
    """
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_event_dict(
    _logger: WrappedLogger,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Structlog processor that redacts PII from log event dicts.

    Only inspects top-level string values (log events are flat).  Metadata
    keys like ``timestamp``, ``level``, and ``request_id`` are skipped.
    """
    for key in list(event_dict):
        if key in _SKIP_KEYS:
            continue
        value = event_dict[key]
        if isinstance(value, str):
            event_dict[key] = redact_pii(value)
    return event_dict
