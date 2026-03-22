"""Add rendering_gate_config to project.

Revision ID: w8x9y0z1a2b3
Revises: x8y9z0a1b2c3
Create Date: 2026-03-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "w8x9y0z1a2b3"
down_revision: str | None = "x8y9z0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "rendering_gate_config",
            sa.JSON(),
            nullable=True,
            comment="Per-project rendering gate configuration (mode, thresholds, target clients)",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "rendering_gate_config")
