"""Add config_json to design_connections.

Revision ID: a0b1c2d3e4f5
Revises: g7f6e5d4c3b2
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: str | None = "g7f6e5d4c3b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "design_connections",
        sa.Column(
            "config_json",
            JSON,
            nullable=True,
            comment="Per-connection config: naming convention, section map, button hints",
        ),
    )


def downgrade() -> None:
    op.drop_column("design_connections", "config_json")
