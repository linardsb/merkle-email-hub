"""Provider protocol and shared data structures for brief providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RawAttachment:
    """An attachment from an external platform."""

    filename: str
    url: str
    size_bytes: int | None = None


@dataclass(frozen=True)
class RawResource:
    """A linked resource from an external platform."""

    type: str  # excel/translation/design/document/image/other
    filename: str
    url: str
    size_bytes: int | None = None


@dataclass(frozen=True)
class RawBriefItem:
    """Normalized item from an external platform."""

    external_id: str
    title: str
    description: str
    status: str  # open/in_progress/done/cancelled
    priority: str | None
    assignees: list[str] = field(default_factory=list[str])
    labels: list[str] = field(default_factory=list[str])
    due_date: datetime | None = None
    thumbnail_url: str | None = None
    resources: list[RawResource] = field(default_factory=list[RawResource])
    attachments: list[RawAttachment] = field(default_factory=list[RawAttachment])


@runtime_checkable
class BriefProvider(Protocol):
    """Interface that each platform provider must implement."""

    async def validate_credentials(self, credentials: dict[str, str], project_url: str) -> bool:
        """Test that credentials are valid. Return True or raise."""
        ...

    async def extract_project_id(self, project_url: str) -> str:
        """Extract the platform-specific project/board ID from a URL."""
        ...

    async def list_items(self, credentials: dict[str, str], project_id: str) -> list[RawBriefItem]:
        """Fetch all tasks/issues/cards from the external project."""
        ...

    async def get_item(
        self, credentials: dict[str, str], project_id: str, item_id: str
    ) -> RawBriefItem:
        """Fetch a single task/issue with full detail."""
        ...
