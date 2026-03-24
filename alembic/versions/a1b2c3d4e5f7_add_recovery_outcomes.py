"""Add recovery_outcomes table for adaptive fixer selection.

Revision ID: a1b2c3d4e5f7
Revises: z0a1b2c3d4e5
Create Date: 2026-03-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "z0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recovery_outcomes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("check_name", sa.String(64), nullable=False),
        sa.Column("agent_routed", sa.String(64), nullable=False),
        sa.Column("failure_fingerprint", sa.String(128), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("iterations_needed", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recovery_outcomes_check_name", "recovery_outcomes", ["check_name"])
    op.create_index("ix_recovery_outcomes_agent_routed", "recovery_outcomes", ["agent_routed"])
    op.create_index("ix_recovery_outcomes_project_id", "recovery_outcomes", ["project_id"])
    op.create_index(
        "ix_recovery_outcome_check_agent",
        "recovery_outcomes",
        ["check_name", "agent_routed"],
    )


def downgrade() -> None:
    op.drop_index("ix_recovery_outcome_check_agent", table_name="recovery_outcomes")
    op.drop_index("ix_recovery_outcomes_project_id", table_name="recovery_outcomes")
    op.drop_index("ix_recovery_outcomes_agent_routed", table_name="recovery_outcomes")
    op.drop_index("ix_recovery_outcomes_check_name", table_name="recovery_outcomes")
    op.drop_table("recovery_outcomes")
