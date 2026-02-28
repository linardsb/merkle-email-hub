"""Database models for email component library."""

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.models import TimestampMixin


class Component(Base, TimestampMixin):
    """Reusable email component (e.g., header, CTA button, hero block)."""

    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    versions: Mapped[list["ComponentVersion"]] = relationship(
        back_populates="component",
        cascade="all, delete-orphan",
        order_by="ComponentVersion.version_number.desc()",
    )


class ComponentVersion(Base, TimestampMixin):
    """Versioned snapshot of a component's source code."""

    __tablename__ = "component_versions"
    __table_args__ = (
        UniqueConstraint("component_id", "version_number", name="uq_component_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("components.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    html_source: Mapped[str] = mapped_column(Text, nullable=False)
    css_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    component: Mapped[Component] = relationship(back_populates="versions")
