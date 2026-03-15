"""Add slot_definitions to component_versions.

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
"""

import sqlalchemy as sa

from alembic import op

revision = "g3h4i5j6k7l8"
down_revision = "f2a3b4c5d6e7"


def upgrade() -> None:
    op.add_column(
        "component_versions",
        sa.Column("slot_definitions", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("component_versions", "slot_definitions")
