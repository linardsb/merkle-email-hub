"""Add search_embedding column to components table.

Revision ID: o0p1q2r3s4t5
Revises: n9o0p1q2r3s4
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "o0p1q2r3s4t5"
down_revision = "n9o0p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("components", sa.Column("search_embedding", Vector(1024), nullable=True))


def downgrade() -> None:
    op.drop_column("components", "search_embedding")
