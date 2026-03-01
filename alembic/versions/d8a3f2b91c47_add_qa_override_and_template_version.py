"""add qa override and template version link

Revision ID: d8a3f2b91c47
Revises: c7d2e5f19a83
Create Date: 2026-03-01 09:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8a3f2b91c47"
down_revision: str | None = "c7d2e5f19a83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Make build_id nullable on qa_results (QA can run on raw HTML without a build)
    op.alter_column("qa_results", "build_id", existing_type=sa.Integer(), nullable=True)

    # 2. Add template_version_id FK for audit linkage
    op.add_column(
        "qa_results",
        sa.Column(
            "template_version_id",
            sa.Integer(),
            sa.ForeignKey("template_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_qa_results_template_version_id"),
        "qa_results",
        ["template_version_id"],
        unique=False,
    )

    # 3. Add CASCADE to qa_checks FK (was missing in original migration)
    op.drop_constraint("qa_checks_qa_result_id_fkey", "qa_checks", type_="foreignkey")
    op.create_foreign_key(
        "qa_checks_qa_result_id_fkey",
        "qa_checks",
        "qa_results",
        ["qa_result_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 4. Create qa_overrides table
    op.create_table(
        "qa_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("qa_result_id", sa.Integer(), nullable=False),
        sa.Column("overridden_by_id", sa.Integer(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("checks_overridden", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["qa_result_id"],
            ["qa_results.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["overridden_by_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("qa_result_id"),
    )
    op.create_index(op.f("ix_qa_overrides_id"), "qa_overrides", ["id"], unique=False)
    op.create_index(
        op.f("ix_qa_overrides_qa_result_id"),
        "qa_overrides",
        ["qa_result_id"],
        unique=True,
    )


def downgrade() -> None:
    # Drop qa_overrides table
    op.drop_index(op.f("ix_qa_overrides_qa_result_id"), table_name="qa_overrides")
    op.drop_index(op.f("ix_qa_overrides_id"), table_name="qa_overrides")
    op.drop_table("qa_overrides")

    # Revert qa_checks FK to original (no CASCADE)
    op.drop_constraint("qa_checks_qa_result_id_fkey", "qa_checks", type_="foreignkey")
    op.create_foreign_key(
        "qa_checks_qa_result_id_fkey",
        "qa_checks",
        "qa_results",
        ["qa_result_id"],
        ["id"],
    )

    # Remove template_version_id column
    op.drop_index(op.f("ix_qa_results_template_version_id"), table_name="qa_results")
    op.drop_column("qa_results", "template_version_id")

    # Revert build_id to NOT NULL
    op.alter_column("qa_results", "build_id", existing_type=sa.Integer(), nullable=False)
