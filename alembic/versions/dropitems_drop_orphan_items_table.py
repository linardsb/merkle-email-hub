"""drop orphan items table (F007 cleanup)

Revision ID: drop_items_table
Revises: sec03_disable_rls
Create Date: 2026-05-05 17:30:00.000000

The ``items`` table is a leftover from the ``app/example/`` demo CRUD
that was deleted in commit ``eddcd1ac`` (F007 closure, PR #40). The
SQLAlchemy model is gone but the table + 3 indexes still exist in the
DB, surfacing on every CI run as advisory ``alembic check`` drift.

This migration drops the table and its 3 indexes. RLS policies on the
table were already dropped in ``sec03_disable_rls``; nothing else
references it.

This is one slice of the broader model<->schema drift cataloged in
``.agents/deferred-items.json::tech-debt-alembic-schema-drift``. The
remaining ~30 timestamp-type and NOT-NULL drifts are deferred to
Session 19 (backend sweep) where they can be paired with F057
migration squash.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "drop_items_table"
down_revision: str | None = "sec03_disable_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # IF EXISTS guards make the migration safe to apply on environments
    # where the table or indexes were already dropped manually.
    op.execute("DROP INDEX IF EXISTS ix_items_deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_items_name")
    op.execute("DROP INDEX IF EXISTS ix_items_id")
    op.execute("DROP TABLE IF EXISTS items")


def downgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_items_id", "items", ["id"], unique=False)
    op.create_index("ix_items_name", "items", ["name"], unique=False)
    op.create_index("ix_items_deleted_at", "items", ["deleted_at"], unique=False)
