"""add briefs tables

Revision ID: u5v6w7x8y9z0
Revises: 2eb1d5b05ad3
Create Date: 2026-03-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "u5v6w7x8y9z0"
down_revision: str | None = "2eb1d5b05ad3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brief_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("project_url", sa.String(length=500), nullable=False),
        sa.Column("external_project_id", sa.String(length=200), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("credential_last4", sa.String(length=4), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="connected"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brief_connections_id"), "brief_connections", ["id"], unique=False)
    op.create_index(
        op.f("ix_brief_connections_platform"), "brief_connections", ["platform"], unique=False
    )
    op.create_index(
        op.f("ix_brief_connections_project_id"), "brief_connections", ["project_id"], unique=False
    )

    op.create_table(
        "brief_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("brief_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("assignees", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("labels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id", "external_id", name="uq_brief_items_connection_external"
        ),
    )
    op.create_index(op.f("ix_brief_items_id"), "brief_items", ["id"], unique=False)
    op.create_index(
        op.f("ix_brief_items_connection_id"), "brief_items", ["connection_id"], unique=False
    )

    op.create_table(
        "brief_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("brief_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brief_resources_id"), "brief_resources", ["id"], unique=False)
    op.create_index(
        op.f("ix_brief_resources_item_id"), "brief_resources", ["item_id"], unique=False
    )

    op.create_table(
        "brief_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("brief_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brief_attachments_id"), "brief_attachments", ["id"], unique=False)
    op.create_index(
        op.f("ix_brief_attachments_item_id"), "brief_attachments", ["item_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("brief_attachments")
    op.drop_table("brief_resources")
    op.drop_table("brief_items")
    op.drop_table("brief_connections")
