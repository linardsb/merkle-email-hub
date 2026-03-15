"""Add design import tables.

Revision ID: j5k6l7m8n9o0
Revises: i4j5k6l7m8n9
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "j5k6l7m8n9o0"
down_revision: str | None = "i4j5k6l7m8n9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "design_imports",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("design_connections.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("selected_node_ids", sa.JSON(), nullable=False),
        sa.Column("structure_json", sa.JSON(), nullable=True),
        sa.Column("generated_brief", sa.Text(), nullable=True),
        sa.Column(
            "result_template_id",
            sa.Integer(),
            sa.ForeignKey("templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "design_import_assets",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "import_id",
            sa.Integer(),
            sa.ForeignKey("design_imports.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("node_name", sa.String(300), nullable=False),
        sa.Column("file_path", sa.String(255), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(10), nullable=False, server_default="png"),
        sa.Column("usage", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("design_import_assets")
    op.drop_table("design_imports")
