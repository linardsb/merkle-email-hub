"""Add webhook_id to design_connections.

Revision ID: g7f6e5d4c3b2
Revises: f6e5d4c3b2a1
Create Date: 2026-03-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "g7f6e5d4c3b2"
down_revision: str | None = "f6e5d4c3b2a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "design_connections",
        sa.Column("webhook_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("design_connections", "webhook_id")
