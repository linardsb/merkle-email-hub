"""add collaborative_documents

Revision ID: d3e4f5a6b7c8
Revises: c5d6e7f8g9h0
Create Date: 2026-03-17 21:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c5d6e7f8g9h0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collaborative_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("room_id", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("state", sa.LargeBinary(), nullable=False, server_default=sa.text("'\\x'")),
        sa.Column(
            "pending_updates",
            sa.LargeBinary(),
            nullable=False,
            server_default=sa.text("'\\x'"),
        ),
        sa.Column(
            "pending_update_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "last_compacted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "document_size_bytes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("collaborative_documents")
