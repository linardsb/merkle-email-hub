"""Add default_tokens to component_versions.

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
"""

import sqlalchemy as sa

from alembic import op

revision = "h4i5j6k7l8m9"
down_revision = "g3h4i5j6k7l8"


def upgrade() -> None:
    op.add_column(
        "component_versions",
        sa.Column(
            "default_tokens",
            sa.JSON(),
            nullable=True,
            comment="Design token defaults (colors, fonts — enables design-system-agnostic usage)",
        ),
    )


def downgrade() -> None:
    op.drop_column("component_versions", "default_tokens")
