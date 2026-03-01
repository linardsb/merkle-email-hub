"""seed persona presets

Revision ID: b4f1e8a23c71
Revises: a3e7c1d48f52
Create Date: 2026-03-01 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4f1e8a23c71"
down_revision: str | None = "a3e7c1d48f52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    personas = sa.table(
        "personas",
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.Text),
        sa.column("email_client", sa.String),
        sa.column("device_type", sa.String),
        sa.column("dark_mode", sa.Boolean),
        sa.column("viewport_width", sa.Integer),
        sa.column("os_name", sa.String),
        sa.column("is_preset", sa.Boolean),
    )

    op.bulk_insert(
        personas,
        [
            {
                "name": "Gmail Desktop",
                "slug": "gmail-desktop",
                "description": "Gmail on Chrome desktop — most common B2B reader",
                "email_client": "gmail",
                "device_type": "desktop",
                "dark_mode": False,
                "viewport_width": 600,
                "os_name": "macOS",
                "is_preset": True,
            },
            {
                "name": "Outlook 365",
                "slug": "outlook-365",
                "description": "Outlook 365 on Windows — Word rendering engine",
                "email_client": "outlook-365",
                "device_type": "desktop",
                "dark_mode": False,
                "viewport_width": 600,
                "os_name": "Windows",
                "is_preset": True,
            },
            {
                "name": "Apple Mail Dark",
                "slug": "apple-mail-dark",
                "description": "Apple Mail with dark mode on macOS",
                "email_client": "apple-mail",
                "device_type": "desktop",
                "dark_mode": True,
                "viewport_width": 600,
                "os_name": "macOS",
                "is_preset": True,
            },
            {
                "name": "iPhone Mail",
                "slug": "iphone-mail",
                "description": "Default Mail.app on iPhone — most common mobile reader",
                "email_client": "apple-mail",
                "device_type": "mobile",
                "dark_mode": False,
                "viewport_width": 375,
                "os_name": "iOS",
                "is_preset": True,
            },
            {
                "name": "Samsung Mail Dark",
                "slug": "samsung-mail-dark",
                "description": "Samsung Email on Galaxy device with dark mode",
                "email_client": "samsung-mail",
                "device_type": "mobile",
                "dark_mode": True,
                "viewport_width": 360,
                "os_name": "Android",
                "is_preset": True,
            },
            {
                "name": "Outlook Classic",
                "slug": "outlook-classic",
                "description": "Outlook 2019/2021 desktop — legacy Word engine",
                "email_client": "outlook-2019",
                "device_type": "desktop",
                "dark_mode": False,
                "viewport_width": 600,
                "os_name": "Windows",
                "is_preset": True,
            },
            {
                "name": "Gmail Mobile",
                "slug": "gmail-mobile",
                "description": "Gmail app on Android — limited CSS support",
                "email_client": "gmail",
                "device_type": "mobile",
                "dark_mode": False,
                "viewport_width": 360,
                "os_name": "Android",
                "is_preset": True,
            },
            {
                "name": "Yahoo Mail",
                "slug": "yahoo-mail",
                "description": "Yahoo Mail on desktop — strips some CSS",
                "email_client": "yahoo",
                "device_type": "desktop",
                "dark_mode": False,
                "viewport_width": 600,
                "os_name": "Windows",
                "is_preset": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM personas WHERE is_preset = true AND slug IN ("
        "'gmail-desktop', 'outlook-365', 'apple-mail-dark', 'iphone-mail', "
        "'samsung-mail-dark', 'outlook-classic', 'gmail-mobile', 'yahoo-mail')"
    )
