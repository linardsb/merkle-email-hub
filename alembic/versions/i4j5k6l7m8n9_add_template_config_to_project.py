"""Add template_config to project.

Revision ID: i4j5k6l7m8n9
Revises: h4i5j6k7l8m9
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "i4j5k6l7m8n9"
down_revision: str | None = "h4i5j6k7l8m9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "template_config",
            sa.JSON(),
            nullable=True,
            comment="Per-project template registry configuration (overrides, custom sections, disabled/preferred)",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "template_config")
