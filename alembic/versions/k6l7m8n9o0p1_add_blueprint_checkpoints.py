"""Add blueprint_checkpoints table.

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-03-16 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "k6l7m8n9o0p1"
down_revision: str | None = "j5k6l7m8n9o0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blueprint_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("run_id", sa.String(50), nullable=False, index=True),
        sa.Column("blueprint_name", sa.String(100), nullable=False),
        sa.Column("node_name", sa.String(100), nullable=False),
        sa.Column("node_index", sa.Integer(), nullable=False),
        sa.Column("state_json", postgresql.JSONB(), nullable=False),
        sa.Column("html_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_checkpoint_run_node",
        "blueprint_checkpoints",
        ["run_id", "node_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_checkpoint_run_node", table_name="blueprint_checkpoints")
    op.drop_table("blueprint_checkpoints")
