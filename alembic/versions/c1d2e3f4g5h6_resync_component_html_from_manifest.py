"""resync component HTML from optimised manifest files

Revision ID: c1d2e3f4g5h6
Revises: bf9341e2639a
Create Date: 2026-03-31 16:00:00.000000

"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4g5h6"
down_revision: str | None = "bf9341e2639a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upsert all components from manifest — adds missing, updates existing HTML."""
    from app.components.data.seeds import COMPONENT_SEEDS

    now = datetime.now(UTC)
    conn = op.get_bind()

    for seed in COMPONENT_SEEDS:
        slug = str(seed["slug"])

        # Check if component already exists (non-deleted)
        row = conn.execute(
            sa.text("SELECT id FROM components WHERE slug = :slug AND deleted_at IS NULL"),
            {"slug": slug},
        ).first()

        if row is not None:
            component_id = row[0]

            # Update component metadata
            conn.execute(
                sa.text(
                    "UPDATE components SET name = :name, description = :description, "
                    "category = :category, updated_at = :now WHERE id = :id"
                ),
                {
                    "name": str(seed["name"]),
                    "description": str(seed.get("description", "")),
                    "category": str(seed.get("category", "general")),
                    "now": now,
                    "id": component_id,
                },
            )

            # Update latest version with fresh HTML + slots + tokens
            ver_row = conn.execute(
                sa.text(
                    "SELECT id FROM component_versions "
                    "WHERE component_id = :cid ORDER BY version_number DESC LIMIT 1"
                ),
                {"cid": component_id},
            ).first()

            if ver_row is not None:
                conn.execute(
                    sa.text(
                        "UPDATE component_versions SET "
                        "html_source = :html, css_source = :css, "
                        "compatibility = :compat, slot_definitions = :slots, "
                        "default_tokens = :tokens, updated_at = :now "
                        "WHERE id = :vid"
                    ),
                    {
                        "html": str(seed["html_source"]),
                        "css": str(seed["css_source"]) if seed.get("css_source") else None,
                        "compat": json.dumps(seed.get("compatibility"))
                        if seed.get("compatibility")
                        else None,
                        "slots": json.dumps(seed.get("slot_definitions"))
                        if seed.get("slot_definitions")
                        else None,
                        "tokens": json.dumps(seed.get("default_tokens"))
                        if seed.get("default_tokens")
                        else None,
                        "now": now,
                        "vid": ver_row[0],
                    },
                )
            else:
                # Component exists but no version — create one
                conn.execute(
                    sa.text(
                        "INSERT INTO component_versions "
                        "(component_id, version_number, html_source, css_source, changelog, "
                        "compatibility, slot_definitions, default_tokens, created_by_id, created_at, updated_at) "
                        "VALUES (:cid, 1, :html, :css, :changelog, :compat, :slots, :tokens, 1, :now, :now)"
                    ),
                    {
                        "cid": component_id,
                        "html": str(seed["html_source"]),
                        "css": str(seed["css_source"]) if seed.get("css_source") else None,
                        "changelog": "Resync from optimised manifest",
                        "compat": json.dumps(seed.get("compatibility"))
                        if seed.get("compatibility")
                        else None,
                        "slots": json.dumps(seed.get("slot_definitions"))
                        if seed.get("slot_definitions")
                        else None,
                        "tokens": json.dumps(seed.get("default_tokens"))
                        if seed.get("default_tokens")
                        else None,
                        "now": now,
                    },
                )
        else:
            # New component — insert component + v1
            conn.execute(
                sa.text(
                    "INSERT INTO components (name, slug, description, category, created_by_id, created_at, updated_at) "
                    "VALUES (:name, :slug, :description, :category, 1, :now, :now)"
                ),
                {
                    "name": str(seed["name"]),
                    "slug": slug,
                    "description": str(seed.get("description", "")),
                    "category": str(seed.get("category", "general")),
                    "now": now,
                },
            )

            component_id = conn.execute(
                sa.text("SELECT id FROM components WHERE slug = :slug"),
                {"slug": slug},
            ).scalar_one()

            conn.execute(
                sa.text(
                    "INSERT INTO component_versions "
                    "(component_id, version_number, html_source, css_source, changelog, "
                    "compatibility, slot_definitions, default_tokens, created_by_id, created_at, updated_at) "
                    "VALUES (:cid, 1, :html, :css, :changelog, :compat, :slots, :tokens, 1, :now, :now)"
                ),
                {
                    "cid": component_id,
                    "html": str(seed["html_source"]),
                    "css": str(seed["css_source"]) if seed.get("css_source") else None,
                    "changelog": "Initial seed from optimised manifest",
                    "compat": json.dumps(seed.get("compatibility"))
                    if seed.get("compatibility")
                    else None,
                    "slots": json.dumps(seed.get("slot_definitions"))
                    if seed.get("slot_definitions")
                    else None,
                    "tokens": json.dumps(seed.get("default_tokens"))
                    if seed.get("default_tokens")
                    else None,
                    "now": now,
                },
            )


def downgrade() -> None:
    # Data-only migration — downgrade is a no-op.
    # Original seed migration handles component cleanup.
    pass
