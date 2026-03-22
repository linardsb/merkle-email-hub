"""Add confidence scoring columns to rendering_screenshots.

Revision ID: w7x8y9z0a1b2
Revises: v6w7x8y9z0a1
Create Date: 2026-03-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "w7x8y9z0a1b2"
down_revision: str | None = "v6w7x8y9z0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rendering_screenshots", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.add_column(
        "rendering_screenshots", sa.Column("confidence_breakdown", sa.JSON(), nullable=True)
    )
    op.add_column(
        "rendering_screenshots",
        sa.Column("confidence_recommendations", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rendering_screenshots", "confidence_recommendations")
    op.drop_column("rendering_screenshots", "confidence_breakdown")
    op.drop_column("rendering_screenshots", "confidence_score")
