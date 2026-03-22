"""Add rendering_tests and rendering_screenshots tables.

These tables were defined in app/rendering/models.py but never had a
migration. Subsequent migration w7x8y9z0a1b2 adds columns to
rendering_screenshots, which fails on fresh databases without this.

Revision ID: v6w7x8y9z1b2
Revises: v6w7x8y9z0a1
Create Date: 2026-03-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "v6w7x8y9z1b2"
down_revision: str | None = "v6w7x8y9z0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rendering_tests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_test_id", sa.String(255), nullable=False, index=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default="litmus"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "build_id",
            sa.Integer(),
            sa.ForeignKey("email_builds.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "template_version_id",
            sa.Integer(),
            sa.ForeignKey("template_versions.id"),
            nullable=True,
        ),
        sa.Column("clients_requested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clients_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "submitted_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "rendering_screenshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "rendering_test_id",
            sa.Integer(),
            sa.ForeignKey("rendering_tests.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("client_name", sa.String(100), nullable=False),
        sa.Column("screenshot_url", sa.String(500), nullable=True),
        sa.Column("os", sa.String(50), nullable=False, server_default=""),
        sa.Column("category", sa.String(50), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("rendering_screenshots")
    op.drop_table("rendering_tests")
