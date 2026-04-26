"""Shared fixtures for connector service tests.

Provides an autouse fixture that pins the `get_settings()` callable used by the
four ESP connector services to a real `Settings` instance. Without this, a stray
`MagicMock(spec=Settings)` from another test could leak `credentials.pools` as a
`MagicMock` and trip the connector pool-detection logic.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _connector_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Pin `get_settings` to a real Settings inside the four ESP connector modules.

    Tests that need to override config can still use `patch(...)` inside their
    own scope — the patch context is more local than this fixture.
    """
    real_settings = get_settings()
    for module_path in (
        "app.connectors.braze.service",
        "app.connectors.sfmc.service",
        "app.connectors.adobe.service",
        "app.connectors.taxi.service",
    ):
        monkeypatch.setattr(f"{module_path}.get_settings", lambda: real_settings)
    yield real_settings
