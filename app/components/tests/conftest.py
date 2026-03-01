"""Shared test fixtures for the email components feature."""

from unittest.mock import AsyncMock

import pytest

from app.components.models import Component, ComponentVersion
from app.shared.models import utcnow


def make_component(**overrides: object) -> Component:
    """Factory to create a Component model instance with sensible defaults.

    Args:
        **overrides: Field values to override defaults.

    Returns:
        A Component instance with all fields populated.
    """
    now = utcnow()
    defaults: dict[str, object] = {
        "id": 1,
        "name": "Test Component",
        "slug": "test-component",
        "description": "A test component for testing.",
        "category": "content",
        "created_by_id": 1,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Component(**defaults)


def make_version(**overrides: object) -> ComponentVersion:
    """Factory to create a ComponentVersion instance with sensible defaults.

    Args:
        **overrides: Field values to override defaults.

    Returns:
        A ComponentVersion instance with all fields populated.
    """
    now = utcnow()
    defaults: dict[str, object] = {
        "id": 1,
        "component_id": 1,
        "version_number": 1,
        "html_source": "<table role='presentation'><tr><td>Test</td></tr></table>",
        "css_source": None,
        "changelog": None,
        "compatibility": None,
        "created_by_id": 1,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return ComponentVersion(**defaults)


@pytest.fixture
def sample_component() -> Component:
    """A single default component instance."""
    return make_component()


@pytest.fixture
def sample_components() -> list[Component]:
    """Multiple component instances for list tests."""
    return [
        make_component(id=1, name="Header", slug="header", category="structure"),
        make_component(id=2, name="Footer", slug="footer", category="structure"),
        make_component(id=3, name="CTA Button", slug="cta-button", category="action"),
    ]


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock AsyncSession for repository tests."""
    return AsyncMock()
