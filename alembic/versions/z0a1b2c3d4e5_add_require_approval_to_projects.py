"""Add require_approval_for_export to projects.

Revision ID: z0a1b2c3d4e5
Revises: y9z0a1b2c3d4
Create Date: 2026-03-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "z0a1b2c3d4e5"
down_revision: str | None = "y9z0a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "require_approval_for_export",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Require approval before ESP export",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "require_approval_for_export")
