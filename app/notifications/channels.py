"""Notification channel abstractions — Protocol, dataclasses, and type aliases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

type Severity = str  # "info" | "warning" | "error"


@dataclass(frozen=True, slots=True)
class Notification:
    """A notification to be sent via one or more channels."""

    event: str  # e.g. "qa.regression_detected"
    severity: Severity  # "info", "warning", "error"
    title: str
    body: str
    project_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]


@dataclass(frozen=True, slots=True)
class NotificationResult:
    """Outcome of sending a notification through a single channel."""

    channel: str  # "slack", "teams", "email"
    success: bool
    error: str | None = None


@runtime_checkable
class NotificationChannel(Protocol):
    """Protocol for notification channel implementations."""

    @property
    def name(self) -> str: ...

    async def send(self, notification: Notification) -> NotificationResult: ...
