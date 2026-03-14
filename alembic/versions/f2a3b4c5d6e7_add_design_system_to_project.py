"""add design_system to project

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-14 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "design_system",
            sa.JSON(),
            nullable=True,
            comment="Per-project brand identity (palette, typography, logo, footer, social links)",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "design_system")
