"""Shared database models and mixins."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Get current UTC time with timezone info.

    Single source of truth for UTC timestamps across the application.
    """
    return datetime.now(UTC)


class SoftDeleteMixin:
    """Mixin for soft delete support via deleted_at timestamp.

    Models with this mixin are never physically deleted — instead,
    deleted_at is set to the current UTC time. Queries must filter
    on deleted_at IS NULL to exclude soft-deleted records.
    """

    @declared_attr.directive
    def deleted_at(cls) -> Mapped[datetime | None]:
        return mapped_column(DateTime(timezone=True), nullable=True, default=None, index=True)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps.

    All models should inherit this mixin to automatically track
    when records are created and updated.

    Example:
        class Product(Base, TimestampMixin):
            __tablename__ = "products"
            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str] = mapped_column(String(200))
    """

    @declared_attr.directive
    def created_at(cls) -> Mapped[datetime]:
        """Timestamp when the record was created."""
        return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    @declared_attr.directive
    def updated_at(cls) -> Mapped[datetime]:
        """Timestamp when the record was last updated."""
        return mapped_column(
            DateTime(timezone=True),
            default=utcnow,
            onupdate=utcnow,
            nullable=False,
        )
