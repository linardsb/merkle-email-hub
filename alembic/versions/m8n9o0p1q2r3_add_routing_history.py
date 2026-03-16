"""Add routing_history table for adaptive model tier routing.

Revision ID: m8n9o0p1q2r3
Revises: l7m8n9o0p1q2
Create Date: 2026-03-16
"""

import sqlalchemy as sa

from alembic import op

revision = "m8n9o0p1q2r3"
down_revision = "l7m8n9o0p1q2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "routing_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("agent_name", sa.String(64), nullable=False, index=True),
        sa.Column("project_id", sa.Integer, nullable=True, index=True),
        sa.Column("tier_used", sa.String(16), nullable=False),
        sa.Column("accepted", sa.Boolean, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_routing_history_agent_project",
        "routing_history",
        ["agent_name", "project_id"],
    )


def downgrade() -> None:
    op.drop_table("routing_history")
