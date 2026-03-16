"""Add screenshot_baselines table.

Revision ID: q1r2s3t4u5v6
Revises: o0p1q2r3s4t5
"""

import sqlalchemy as sa

from alembic import op

revision = "q1r2s3t4u5v6"
down_revision = "o0p1q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "screenshot_baselines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("entity_id", sa.Integer(), nullable=False, index=True),
        sa.Column("client_name", sa.String(100), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("image_hash", sa.String(64), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "entity_type", "entity_id", "client_name", name="uq_baseline_entity_client"
        ),
    )


def downgrade() -> None:
    op.drop_table("screenshot_baselines")
