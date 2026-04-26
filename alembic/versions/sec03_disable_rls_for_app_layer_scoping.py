"""disable RLS — tenant scoping moved to app layer

Revision ID: sec03_disable_rls
Revises: z0a1b2c3d4e5
Create Date: 2026-04-26 17:00:00.000000

Tenant isolation is now enforced at the application layer via
`app.core.scoped_db.get_scoped_db` + per-repo `scoped_access` filters
(see plan `tech-debt-03-multi-tenant-isolation.md` Approach B and the
helper at `app/core/scoped_db.py`).

The RLS policies created by ``fdd89fceac29`` (projects, client_orgs)
and ``e5f2a9b73d14`` (users, documents, components, items) were
non-functional in practice: every request used the application-owned
DB role which bypasses RLS, so the policies never executed and the
``app.current_role`` GUCs they referenced were never set. Keeping
them is misleading documentation.

This migration drops the policies and disables RLS on the affected
tables. Soft-delete columns added in ``e5f2a9b73d14`` are kept —
they're in active use by the ORM models and their `deleted_at` indexes.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "sec03_disable_rls"
down_revision: str | None = "d2e3f4g5h6i7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables touched by `e5f2a9b73d14` with `{table}_tenant_isolation` policies.
_RLS_TABLES_GENERIC = ("documents", "components", "items")


def upgrade() -> None:
    # Policies from e5f2a9b73d14
    op.execute("DROP POLICY IF EXISTS users_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    for table in _RLS_TABLES_GENERIC:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Policies from fdd89fceac29
    op.execute("DROP POLICY IF EXISTS project_isolation ON projects")
    op.execute("ALTER TABLE projects DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS client_org_isolation ON client_orgs")
    op.execute("ALTER TABLE client_orgs DISABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    # Restore RLS exactly as the upstream migrations created it.
    # fdd89fceac29 — projects + client_orgs
    op.execute("ALTER TABLE client_orgs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY client_org_isolation ON client_orgs
            USING (
                id = current_setting('app.current_client_id', true)::int
                OR current_setting('app.current_role', true) = 'admin'
            )
    """)
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY project_isolation ON projects
            USING (
                client_org_id = current_setting('app.current_client_id', true)::int
                OR current_setting('app.current_role', true) = 'admin'
            )
    """)

    # e5f2a9b73d14 — users + generic RLS tables
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY users_isolation ON users
            USING (
                id = current_setting('app.current_user_id', true)::int
                OR current_setting('app.current_role', true) = 'admin'
            )
    """)
    for table in _RLS_TABLES_GENERIC:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
                USING (
                    current_setting('app.current_role', true) = 'admin'
                    OR current_setting('app.current_role', true) IS NOT NULL
                )
        """)
