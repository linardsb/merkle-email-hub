"""add memory_entries table

Revision ID: f1a2b3c4d5e6
Revises: e5f2a9b73d14
Create Date: 2026-03-06

"""

from collections.abc import Sequence

import pgvector.sqlalchemy.vector
import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e5f2a9b73d14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_entries",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("agent_type", sa.String(length=50), nullable=False),
        sa.Column("memory_type", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=1024),
            nullable=True,
        ),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("decay_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="agent"),
        sa.Column("source_agent", sa.String(length=50), nullable=True),
        sa.Column("is_evergreen", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
    )

    # Individual column indexes
    op.create_index("ix_memory_entries_id", "memory_entries", ["id"])
    op.create_index("ix_memory_entries_agent_type", "memory_entries", ["agent_type"])
    op.create_index("ix_memory_entries_memory_type", "memory_entries", ["memory_type"])
    op.create_index("ix_memory_entries_project_id", "memory_entries", ["project_id"])

    # Composite indexes
    op.create_index("ix_memory_project_agent", "memory_entries", ["project_id", "agent_type"])
    op.create_index("ix_memory_type_decay", "memory_entries", ["memory_type", "decay_weight"])

    # HNSW index for fast vector similarity search
    op.execute(
        "CREATE INDEX ix_memory_entries_embedding_hnsw "
        "ON memory_entries USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_table("memory_entries")
