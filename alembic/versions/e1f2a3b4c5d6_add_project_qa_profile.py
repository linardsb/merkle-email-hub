"""add project qa_profile

Revision ID: e1f2a3b4c5d6
Revises: d8e9f0a1b2c3
Create Date: 2026-03-12 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "qa_profile",
            sa.JSON(),
            nullable=True,
            comment="Per-project QA check configuration overrides",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "qa_profile")
