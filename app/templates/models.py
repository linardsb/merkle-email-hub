"""Database models for email templates."""

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.models import SoftDeleteMixin, TimestampMixin


class Template(Base, TimestampMixin, SoftDeleteMixin):
    """Email template belonging to a project."""

    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_line: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preheader_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    versions: Mapped[list["TemplateVersion"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateVersion.version_number.desc()",
    )


class TemplateVersion(Base, TimestampMixin):
    """Immutable versioned snapshot of a template's source code."""

    __tablename__ = "template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_template_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("templates.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    html_source: Mapped[str] = mapped_column(Text, nullable=False)
    css_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    template: Mapped[Template] = relationship(back_populates="versions")
