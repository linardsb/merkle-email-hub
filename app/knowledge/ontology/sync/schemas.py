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

    new_clients: list[str] = field(default_factory=lambda: list[str]())
    new_properties: list[str] = field(default_factory=lambda: list[str]())
    updated_support: list[tuple[str, str, str, str]] = field(
        default_factory=lambda: list[tuple[str, str, str, str]]()
    )
    new_support: list[tuple[str, str, str]] = field(
        default_factory=lambda: list[tuple[str, str, str]]()
    )
    unchanged_count: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(
            self.new_clients or self.new_properties or self.updated_support or self.new_support
        )


@dataclass(frozen=True)
class ChangelogEntry:
    """A single change detected during sync."""

    property_id: str
    client_id: str
    old_level: str | None  # None for new entries
    new_level: str
    source: str  # "caniemail"


@dataclass
class SyncReport:
    """Result of a sync operation."""

    new_properties: int = 0
    updated_levels: int = 0
    new_clients: int = 0
    changelog: list[ChangelogEntry] = field(default_factory=lambda: list[ChangelogEntry]())
    errors: list[str] = field(default_factory=lambda: list[str]())
    dry_run: bool = False
    commit_sha: str = ""


@dataclass
class SyncState:
    """Persisted in Redis — tracks last successful sync."""

    last_sync_at: datetime | None = None
    last_commit_sha: str = ""
    features_synced: int = 0
    error_count: int = 0


@dataclass
class SyncStatus:
    """Computed sync status for API responses."""

    last_sync_at: str | None = None
    last_commit_sha: str | None = None
    features_synced: int = 0
    error_count: int = 0
    last_report: dict[str, object] | None = None
