"""In-memory progress tracking for long-running operations."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar

from app.core.logging import get_logger

logger = get_logger(__name__)


class OperationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEntry:
    """Single operation's progress state."""

    operation_id: str
    operation_type: str  # "rendering", "qa_scan", "design_sync", "export", "blueprint"
    status: OperationStatus = OperationStatus.PENDING
    progress: int = 0  # 0-100
    message: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None


class ProgressTracker:
    """In-memory progress store for long-running operations.

    Thread-safe via lock. Entries auto-expire after configurable max_age.
    """

    _store: ClassVar[dict[str, ProgressEntry]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def start(cls, operation_id: str, operation_type: str) -> ProgressEntry:
        """Register a new operation and return its entry."""
        entry = ProgressEntry(operation_id=operation_id, operation_type=operation_type)
        with cls._lock:
            cls._store[operation_id] = entry
        logger.info("progress.started", operation_id=operation_id, operation_type=operation_type)
        return entry

    @classmethod
    def update(
        cls,
        operation_id: str,
        *,
        progress: int | None = None,
        status: OperationStatus | None = None,
        message: str | None = None,
        error: str | None = None,
    ) -> ProgressEntry | None:
        """Update an existing operation's progress. Returns None if not found."""
        with cls._lock:
            entry = cls._store.get(operation_id)
            if not entry:
                return None
            if progress is not None:
                entry.progress = min(max(progress, 0), 100)
            if status is not None:
                entry.status = status
            if message is not None:
                entry.message = message
            if error is not None:
                entry.error = error
            entry.updated_at = datetime.now(UTC)
        return entry

    @classmethod
    def get(cls, operation_id: str) -> ProgressEntry | None:
        """Get an operation's progress entry."""
        with cls._lock:
            return cls._store.get(operation_id)

    @classmethod
    def get_active(cls) -> list[ProgressEntry]:
        """Return all in-flight (pending or processing) operations."""
        with cls._lock:
            return [
                e
                for e in cls._store.values()
                if e.status in (OperationStatus.PENDING, OperationStatus.PROCESSING)
            ]

    @classmethod
    def cleanup_completed(cls, max_age_seconds: int = 300) -> int:
        """Remove completed/failed entries older than max_age. Returns count removed."""
        now = datetime.now(UTC)
        with cls._lock:
            to_remove = [
                k
                for k, v in cls._store.items()
                if v.status in (OperationStatus.COMPLETED, OperationStatus.FAILED)
                and (now - v.updated_at).total_seconds() > max_age_seconds
            ]
            for k in to_remove:
                del cls._store[k]
        if to_remove:
            logger.debug("progress.cleanup", removed=len(to_remove))
        return len(to_remove)

    @classmethod
    def clear(cls) -> None:
        """Clear all entries. For testing only."""
        with cls._lock:
            cls._store.clear()
