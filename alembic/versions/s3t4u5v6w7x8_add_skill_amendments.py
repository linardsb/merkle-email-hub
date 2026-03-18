"""add skill_amendments table

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-03-18
"""

import sqlalchemy as sa

from alembic import op

revision = "s3t4u5v6w7x8"
down_revision = "r2s3t4u5v6w7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skill_amendments",
        sa.Column("id", sa.String(12), primary_key=True),
        sa.Column("agent_name", sa.String(50), nullable=False, index=True),
        sa.Column("skill_file", sa.String(200), nullable=False),
        sa.Column("section", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("source_pattern_id", sa.String(12), nullable=False),
        sa.Column("source_template_id", sa.String(50), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("review_reason", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("skill_amendments")
