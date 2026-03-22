"""update column layout components to self-contained HTML blocks

Revision ID: v6w7x8y9z0a1
Revises: u5v6w7x8y9z0
Create Date: 2026-03-22 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "v6w7x8y9z0a1"
down_revision: str | None = "u5v6w7x8y9z0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Slugs affected by this migration
_UPDATED_SLUGS = [
    "email-shell",
    "column-layout-2",
    "column-layout-3",
    "column-layout-4",
    "reverse-column",
]


def upgrade() -> None:
    """Update component HTML from seeds.py for column layouts and shell.

    Column Layout 2/3/4 and Reverse Column previously started with bare <tr>,
    which is invalid inside the shell's <div> container. All components now
    follow the self-contained block pattern (outer MSO wrapper + full-width table).
    The Email Shell body container changed from <table><tr><td> to plain <div>.
    """
    from app.components.data.seeds import COMPONENT_SEEDS

    conn = op.get_bind()

    # Build lookup: slug -> seed data
    seeds_by_slug = {s["slug"]: s for s in COMPONENT_SEEDS}

    for slug in _UPDATED_SLUGS:
        seed = seeds_by_slug.get(slug)
        if seed is None:
            continue

        # Update the latest version's html_source for this component
        conn.execute(
            sa.text(
                "UPDATE component_versions SET html_source = :html "
                "WHERE component_id = ("
                "  SELECT id FROM components WHERE slug = :slug"
                ") AND id = ("
                "  SELECT cv.id FROM component_versions cv "
                "  JOIN components c ON cv.component_id = c.id "
                "  WHERE c.slug = :slug "
                "  ORDER BY cv.version_number DESC LIMIT 1"
                ")"
            ),
            {"html": seed["html_source"], "slug": slug},
        )


def downgrade() -> None:
    # Downgrade is not practical for HTML content changes — the old HTML
    # is not stored anywhere except git history. Re-run seed-demo to restore.
    pass
