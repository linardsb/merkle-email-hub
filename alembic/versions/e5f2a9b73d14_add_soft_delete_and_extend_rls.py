"""add soft delete columns and extend RLS to more tables

Revision ID: e5f2a9b73d14
Revises: d8a3f2b91c47
Create Date: 2026-03-06 16:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f2a9b73d14"
down_revision: str | None = "d8a3f2b91c47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that need a deleted_at column for soft delete support.
# Templates, projects, and approval_requests already have it.
SOFT_DELETE_TABLES = ["users", "items", "documents", "tags", "components"]

# Tables to extend Row-Level Security to (client_orgs and projects already have it).
RLS_TABLES_WITH_CLIENT_ORG = ["documents", "components", "items"]


def upgrade() -> None:
    # --- Add deleted_at columns ---
    for table in SOFT_DELETE_TABLES:
        op.add_column(
            table,
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(f"ix_{table}_deleted_at", table, ["deleted_at"])

    # --- Extend RLS to more tables ---
    for table in RLS_TABLES_WITH_CLIENT_ORG:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
                USING (
                    current_setting('app.current_role', true) = 'admin'
                    OR current_setting('app.current_role', true) IS NOT NULL
                )
        """)

    # --- RLS on users table (users can only see themselves unless admin) ---
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY users_isolation ON users
            USING (
                id = current_setting('app.current_user_id', true)::int
                OR current_setting('app.current_role', true) = 'admin'
            )
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS users_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")

    for table in RLS_TABLES_WITH_CLIENT_ORG:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop deleted_at columns
    for table in SOFT_DELETE_TABLES:
        op.drop_index(f"ix_{table}_deleted_at", table_name=table)
        op.drop_column(table, "deleted_at")
