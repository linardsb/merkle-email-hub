"""Database models for email component library."""

from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.models import SoftDeleteMixin, TimestampMixin

__all__ = ["Component", "ComponentQAResult", "ComponentVersion"]


class Component(Base, TimestampMixin, SoftDeleteMixin):
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
    compatibility: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    slot_definitions: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    component: Mapped[Component] = relationship(back_populates="versions")
    qa_results: Mapped[list["ComponentQAResult"]] = relationship(
        back_populates="component_version", cascade="all, delete-orphan", lazy="selectin"
    )


class ComponentQAResult(Base, TimestampMixin):
    """Links a component version to its QA result with denormalised compatibility."""

    __tablename__ = "component_qa_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    component_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("component_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qa_result_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("qa_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalised compatibility snapshot from css_support check
    # e.g. {"gmail_web": "full", "outlook_2019": "partial", "outlook_2016": "none"}
    compatibility: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)

    component_version: Mapped[ComponentVersion] = relationship(back_populates="qa_results")
