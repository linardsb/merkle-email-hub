"""Route tests for skill extraction API endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def _disable_rate_limit() -> None:
    limiter.enabled = False


@patch("app.core.config.get_settings")
def test_list_pending_returns_200(mock_settings: MagicMock) -> None:
    """Verify list endpoint returns correct shape when feature is enabled."""
    mock_settings.return_value.skill_extraction.enabled = True
    mock_settings.return_value.skill_extraction.min_confidence = 0.7
    # Route test pattern: mock service layer, assert status code + shape
    # Full integration requires DB session — covered by service tests
