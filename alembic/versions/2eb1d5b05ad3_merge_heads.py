"""merge heads

Revision ID: 2eb1d5b05ad3
Revises: d3e4f5a6b7c8, t4u5v6w7x8y9
Create Date: 2026-03-19 06:45:24.542148

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "2eb1d5b05ad3"
down_revision: str | None = ("d3e4f5a6b7c8", "t4u5v6w7x8y9")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
