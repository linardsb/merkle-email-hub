"""add rls policies for tenant isolation

Revision ID: fdd89fceac29
Revises: 2bac390231df
Create Date: 2026-02-28 09:34:38.691068

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fdd89fceac29"
down_revision: str | None = "2bac390231df"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Row-Level Security on client_orgs ---
    op.execute("ALTER TABLE client_orgs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY client_org_isolation ON client_orgs
            USING (
                id = current_setting('app.current_client_id', true)::int
                OR current_setting('app.current_role', true) = 'admin'
            )
    """)

    # --- Row-Level Security on projects ---
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY project_isolation ON projects
            USING (
                client_org_id = current_setting('app.current_client_id', true)::int
                OR current_setting('app.current_role', true) = 'admin'
            )
    """)


def downgrade() -> None:
    # Drop RLS policies and disable RLS
    op.execute("DROP POLICY IF EXISTS project_isolation ON projects")
    op.execute("ALTER TABLE projects DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS client_org_isolation ON client_orgs")
    op.execute("ALTER TABLE client_orgs DISABLE ROW LEVEL SECURITY")

    # Note: not dropping vector extension as other schemas may use it
