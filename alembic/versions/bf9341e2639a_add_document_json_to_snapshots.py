"""Add document_json column to design_token_snapshots.

Revision ID: bf9341e2639a
Revises: a0b1c2d3e4f5
Create Date: 2026-03-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision: str = "bf9341e2639a"
down_revision: str | None = "a0b1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "design_token_snapshots",
        sa.Column(
            "document_json",
            JSON(),
            nullable=True,
            comment="EmailDesignDocument v1 JSON (canonical intermediate representation)",
        ),
    )


def downgrade() -> None:
    op.drop_column("design_token_snapshots", "document_json")
