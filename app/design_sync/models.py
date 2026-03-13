"""Database models for design tool sync."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.models import TimestampMixin


class DesignConnection(Base, TimestampMixin):
    """A connection to an external design tool file."""

    __tablename__ = "design_connections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="connected")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True, index=True
    )
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    snapshots: Mapped[list["DesignTokenSnapshot"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )


class DesignTokenSnapshot(Base, TimestampMixin):
    """A snapshot of design tokens extracted from a connection."""

    __tablename__ = "design_token_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    connection_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("design_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tokens_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    connection: Mapped["DesignConnection"] = relationship(back_populates="snapshots")
