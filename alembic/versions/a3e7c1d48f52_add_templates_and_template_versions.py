"""add templates and template versions

Revision ID: a3e7c1d48f52
Revises: fdd89fceac29
Create Date: 2026-02-28 11:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3e7c1d48f52"
down_revision: str | None = "fdd89fceac29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_line", sa.String(length=500), nullable=True),
        sa.Column("preheader_text", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_templates_id"), "templates", ["id"])
    op.create_index(op.f("ix_templates_project_id"), "templates", ["project_id"])
    op.create_index(op.f("ix_templates_name"), "templates", ["name"])
    op.create_index(op.f("ix_templates_deleted_at"), "templates", ["deleted_at"])

    op.create_table(
        "template_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("html_source", sa.Text(), nullable=False),
        sa.Column("css_source", sa.Text(), nullable=True),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "version_number", name="uq_template_version"),
    )
    op.create_index(op.f("ix_template_versions_id"), "template_versions", ["id"])
    op.create_index(op.f("ix_template_versions_template_id"), "template_versions", ["template_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_template_versions_template_id"), table_name="template_versions")
    op.drop_index(op.f("ix_template_versions_id"), table_name="template_versions")
    op.drop_table("template_versions")
    op.drop_index(op.f("ix_templates_deleted_at"), table_name="templates")
    op.drop_index(op.f("ix_templates_name"), table_name="templates")
    op.drop_index(op.f("ix_templates_project_id"), table_name="templates")
    op.drop_index(op.f("ix_templates_id"), table_name="templates")
    op.drop_table("templates")
