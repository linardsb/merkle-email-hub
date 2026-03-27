"""Add fidelity_json to design_imports for visual fidelity scoring.

Revision ID: a1b2c3d4e5f6
Revises: z0a1b2c3d4e5
Create Date: 2026-03-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "z0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "design_imports",
        sa.Column("fidelity_json", JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("design_imports", "fidelity_json")
