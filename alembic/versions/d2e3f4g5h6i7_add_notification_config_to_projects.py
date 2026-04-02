"""add notification_config to projects

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2026-04-02 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e3f4g5h6i7"
down_revision: str | None = "c1d2e3f4g5h6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "notification_config",
            sa.JSON(),
            nullable=True,
            comment="Per-project notification channel overrides (slack/teams/email endpoints)",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "notification_config")
