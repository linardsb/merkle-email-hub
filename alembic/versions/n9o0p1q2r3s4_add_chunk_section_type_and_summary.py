"""Add section_type and summary to document_chunks.

Revision ID: n9o0p1q2r3s4
Revises: m8n9o0p1q2r3
"""

import sqlalchemy as sa

from alembic import op

revision = "n9o0p1q2r3s4"
down_revision = "m8n9o0p1q2r3"


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("section_type", sa.String(50), nullable=True))
    op.add_column("document_chunks", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "summary")
    op.drop_column("document_chunks", "section_type")
