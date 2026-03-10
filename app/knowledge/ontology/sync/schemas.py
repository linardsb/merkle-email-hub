"""Sync state and diff result schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CanIEmailFeature:
    """Parsed feature from Can I Email repository."""

    slug: str  # e.g., "css-display-flex"
    title: str  # e.g., "display:flex"
    category: str  # "css" or "html"
    last_test_date: str  # ISO date
    stats: dict[str, dict[str, dict[str, str]]]  # family > platform > version: support
    notes: dict[str, str]  # note_num -> text


@dataclass
class SyncDiff:
    """Delta between current ontology and incoming Can I Email data."""

    new_clients: list[str] = field(default_factory=list)
    new_properties: list[str] = field(default_factory=list)
    updated_support: list[tuple[str, str, str, str]] = field(default_factory=list)
    new_support: list[tuple[str, str, str]] = field(default_factory=list)
    unchanged_count: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(
            self.new_clients or self.new_properties or self.updated_support or self.new_support
        )


@dataclass
class SyncState:
    """Persisted in Redis — tracks last successful sync."""

    last_sync_at: datetime | None = None
    last_commit_sha: str = ""
    features_synced: int = 0
    error_count: int = 0
