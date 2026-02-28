"""Shared test fixtures for the example items feature."""

from unittest.mock import AsyncMock

import pytest

from app.example.models import Item
from app.shared.models import utcnow


def make_item(**overrides: object) -> Item:
    """Factory to create an Item model instance with sensible defaults.

    Args:
        **overrides: Field values to override defaults.

    Returns:
        An Item instance with all fields populated.
    """
    now = utcnow()
    defaults: dict[str, object] = {
        "id": 1,
        "name": "Example Item",
        "description": "A sample item for testing.",
        "status": "active",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Item(**defaults)


@pytest.fixture
def sample_item() -> Item:
    """A single default item instance."""
    return make_item()


@pytest.fixture
def sample_items() -> list[Item]:
    """Multiple item instances for list tests."""
    return [
        make_item(id=1, name="Alpha Item"),
        make_item(id=2, name="Beta Item", status="archived"),
        make_item(id=3, name="Gamma Item", description="Third item"),
    ]


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock AsyncSession for repository tests."""
    return AsyncMock()
