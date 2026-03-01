"""add compatibility column and seed email components

Revision ID: c7d2e5f19a83
Revises: b4f1e8a23c71
Create Date: 2026-03-01 09:00:00.000000

"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d2e5f19a83"
down_revision: str | None = "b4f1e8a23c71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Slugs used for cleanup in downgrade
_SEED_SLUGS = [
    "email-header",
    "email-footer",
    "cta-button",
    "hero-block",
    "product-card",
    "spacer",
    "social-icons",
    "image-block",
    "text-block",
    "divider",
]


def upgrade() -> None:
    # Part A: Add compatibility JSON column to component_versions
    op.add_column("component_versions", sa.Column("compatibility", sa.JSON(), nullable=True))

    # Part B: Seed 10 email components with initial versions
    # Import here to avoid module-level dependency on app code
    from app.components.data.seeds import COMPONENT_SEEDS

    now = datetime.now(UTC)
    conn = op.get_bind()

    for seed in COMPONENT_SEEDS:
        # Insert component
        conn.execute(
            sa.text(
                "INSERT INTO components (name, slug, description, category, created_by_id, created_at, updated_at) "
                "VALUES (:name, :slug, :description, :category, :created_by_id, :created_at, :updated_at)"
            ),
            {
                "name": seed["name"],
                "slug": seed["slug"],
                "description": seed["description"],
                "category": seed["category"],
                "created_by_id": 1,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Get the inserted component id
        result = conn.execute(
            sa.text("SELECT id FROM components WHERE slug = :slug"),
            {"slug": seed["slug"]},
        )
        component_id = result.scalar_one()

        # Insert initial version
        conn.execute(
            sa.text(
                "INSERT INTO component_versions "
                "(component_id, version_number, html_source, css_source, changelog, compatibility, created_by_id, created_at, updated_at) "
                "VALUES (:component_id, :version_number, :html_source, :css_source, :changelog, :compatibility, :created_by_id, :created_at, :updated_at)"
            ),
            {
                "component_id": component_id,
                "version_number": 1,
                "html_source": seed["html_source"],
                "css_source": seed.get("css_source"),
                "changelog": "Initial seed version",
                "compatibility": json.dumps(seed.get("compatibility"))
                if seed.get("compatibility")
                else None,
                "created_by_id": 1,
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    placeholders = ", ".join(f":s{i}" for i in range(len(_SEED_SLUGS)))
    params = {f"s{i}": slug for i, slug in enumerate(_SEED_SLUGS)}
    conn.execute(
        sa.text(
            f"DELETE FROM component_versions WHERE component_id IN "  # noqa: S608
            f"(SELECT id FROM components WHERE slug IN ({placeholders}))"
        ),
        params,
    )
    conn.execute(
        sa.text(f"DELETE FROM components WHERE slug IN ({placeholders})"),  # noqa: S608
        params,
    )
    op.drop_column("component_versions", "compatibility")
