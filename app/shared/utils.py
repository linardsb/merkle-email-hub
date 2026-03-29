"""Shared utility functions."""

from datetime import datetime


def escape_like(value: str) -> str:
    r"""Escape SQL LIKE/ILIKE wildcard characters.

    Args:
        value: Raw search string that may contain %, _, or \\ characters.

    Returns:
        Escaped string safe for use in LIKE/ILIKE queries.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def format_iso(dt: datetime) -> str:
    """Format datetime as ISO 8601 string."""
    return dt.isoformat()
