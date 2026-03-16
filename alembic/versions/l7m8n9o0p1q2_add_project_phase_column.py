"""Add phase column to projects table.

Revision ID: l7m8n9o0p1q2
Revises: k6l7m8n9o0p1
Create Date: 2026-03-16
"""

import sqlalchemy as sa

from alembic import op

revision = "l7m8n9o0p1q2"
down_revision = "k6l7m8n9o0p1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "phase",
            sa.String(20),
            nullable=False,
            server_default="active",
            comment="Lifecycle phase: active, maintenance, archived",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "phase")
