"""Database models for client organizations and projects."""

from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.models import SoftDeleteMixin, TimestampMixin


class ClientOrg(Base, TimestampMixin):
    """Client organization for multi-tenant isolation."""

    __tablename__ = "client_orgs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    projects: Mapped[list["Project"]] = relationship(
        back_populates="client_org", cascade="all, delete-orphan"
    )


class Project(Base, TimestampMixin, SoftDeleteMixin):
    """Email project workspace scoped to a client organization."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    phase: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="Lifecycle phase: active, maintenance, archived",
    )
    client_org_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("client_orgs.id"), nullable=False, index=True
    )
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target_clients: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, default=None, comment="Ontology client IDs for target audience"
    )
    qa_profile: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None, comment="Per-project QA check configuration overrides"
    )
    design_system: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Per-project brand identity (palette, typography, logo, footer, social links)",
    )
    template_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Per-project template registry configuration (overrides, custom sections, disabled/preferred)",
    )
    rendering_gate_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Per-project rendering gate configuration (mode, thresholds, target clients)",
    )
    export_qa_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Per-project export QA gate configuration (mode, blocking/warning checks)",
    )
    require_approval_for_export: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Require approval before ESP export",
    )

    client_org: Mapped[ClientOrg] = relationship(back_populates="projects")


class ProjectMember(Base, TimestampMixin):
    """Links users to projects with role-based access."""

    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="developer")
