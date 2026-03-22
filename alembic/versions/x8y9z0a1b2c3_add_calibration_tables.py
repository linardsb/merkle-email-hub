"""Add calibration tables for emulator calibration loop.

Revision ID: x8y9z0a1b2c3
Revises: w7x8y9z0a1b2
Create Date: 2026-03-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "x8y9z0a1b2c3"
down_revision: str | None = "w7x8y9z0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calibration_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(50), nullable=False, index=True),
        sa.Column("html_hash", sa.String(64), nullable=False),
        sa.Column("diff_percentage", sa.Float(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=False),
        sa.Column("pixel_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("external_provider", sa.String(50), nullable=False),
        sa.Column("emulator_version", sa.String(64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "calibration_summaries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(50), nullable=False, index=True),
        sa.Column("current_accuracy", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accuracy_trend", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("known_blind_spots", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("last_provider", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("client_id", name="uq_calibration_summary_client"),
    )


def downgrade() -> None:
    op.drop_table("calibration_summaries")
    op.drop_table("calibration_records")
