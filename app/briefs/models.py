"""Database models for brief connections and items."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.models import TimestampMixin


class BriefConnection(Base, TimestampMixin):
    """A connection to an external project management platform."""

    __tablename__ = "brief_connections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    project_url: Mapped[str] = mapped_column(String(500), nullable=False)
    external_project_id: Mapped[str] = mapped_column(String(200), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    credential_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="connected")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True, index=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    items: Mapped[list["BriefItem"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )


class BriefItem(Base, TimestampMixin):
    """A task/issue/card imported from an external platform."""

    __tablename__ = "brief_items"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id", name="uq_brief_items_connection_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    connection_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("brief_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    assignees: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    labels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    connection: Mapped["BriefConnection"] = relationship(back_populates="items")
    resources: Mapped[list["BriefResource"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["BriefAttachment"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class BriefResource(Base):
    """A linked resource (spreadsheet, design file, etc.) from a brief item."""

    __tablename__ = "brief_resources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("brief_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    item: Mapped["BriefItem"] = relationship(back_populates="resources")


class BriefAttachment(Base):
    """A file attachment from a brief item."""

    __tablename__ = "brief_attachments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("brief_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    item: Mapped["BriefItem"] = relationship(back_populates="attachments")
