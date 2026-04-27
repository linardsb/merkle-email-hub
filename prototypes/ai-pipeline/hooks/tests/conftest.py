"""Shared fixtures for hook tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.ai.hooks.registry import HookRegistry


@pytest.fixture
def hook_registry() -> HookRegistry:
    return HookRegistry(active_profile="standard")


@pytest.fixture
def mock_hook_fn() -> AsyncMock:
    return AsyncMock(return_value=None)
