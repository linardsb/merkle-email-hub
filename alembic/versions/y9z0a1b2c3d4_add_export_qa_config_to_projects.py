"""Add export_qa_config to projects.

Revision ID: y9z0a1b2c3d4
Revises: w8x9y0z1a2b3
Create Date: 2026-03-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "y9z0a1b2c3d4"
down_revision: str | None = "w8x9y0z1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "export_qa_config",
            sa.JSON(),
            nullable=True,
            comment="Per-project export QA gate configuration (mode, blocking/warning checks)",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "export_qa_config")
