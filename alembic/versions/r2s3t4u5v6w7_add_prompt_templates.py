"""Add prompt_templates table for versioned prompt store.

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2026-03-17
"""

import sqlalchemy as sa

from alembic import op

revision = "r2s3t4u5v6w7"
down_revision = "q1r2s3t4u5v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("variant", sa.String(64), nullable=False, server_default="default"),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_prompt_templates_agent_variant",
        "prompt_templates",
        ["agent_id", "variant"],
    )
    op.create_index(
        "ix_prompt_templates_active",
        "prompt_templates",
        ["agent_id", "variant", "active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("prompt_templates")
