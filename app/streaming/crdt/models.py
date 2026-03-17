"""Collaborative document persistence model."""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class CollaborativeDocument(Base, TimestampMixin):
    """Persisted Yjs CRDT document state.

    Each room_id maps to one document. The ``state`` column holds the
    compacted Yjs document state (full snapshot). The ``pending_updates``
    column accumulates incremental updates between compactions.
    """

    __tablename__ = "collaborative_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_id: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Room identifier (project:{id}:template:{id})",
    )
    state: Mapped[bytes] = mapped_column(
        sa.LargeBinary,
        nullable=False,
        default=b"",
        comment="Compacted Yjs document state (full snapshot)",
    )
    pending_updates: Mapped[bytes] = mapped_column(
        sa.LargeBinary,
        nullable=False,
        default=b"",
        comment="Accumulated incremental Yjs updates since last compaction",
    )
    pending_update_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        comment="Number of updates since last compaction",
    )
    last_compacted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    document_size_bytes: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        comment="Total document size for quota enforcement",
    )
