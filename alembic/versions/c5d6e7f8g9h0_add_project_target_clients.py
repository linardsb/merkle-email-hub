"""add project target_clients

Revision ID: c5d6e7f8g9h0
Revises: a1b2c3d4e5f6
Create Date: 2026-03-10 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8g9h0"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "target_clients",
            sa.JSON(),
            nullable=True,
            comment="Ontology client IDs for target audience",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "target_clients")
