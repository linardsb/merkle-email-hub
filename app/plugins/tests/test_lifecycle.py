"""Tests for plugin lifecycle management."""

from __future__ import annotations

from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.plugins.lifecycle import PluginLifecycleManager
from app.plugins.registry import PluginInstance, PluginRegistry
from app.plugins.sandbox import PluginSandbox


def _make_manifest(name: str = "test-plugin") -> MagicMock:
    manifest = MagicMock()
    manifest.name = name
    return manifest


def _make_plugin(
    name: str = "test-plugin",
    status: str = "active",
    *,
    has_setup: bool = True,
    has_teardown: bool = True,
    has_health: bool = False,
) -> PluginInstance:
    module = ModuleType(f"plugin_{name}")
    if has_setup:
        module.setup = AsyncMock()  # type: ignore[attr-defined]
    if has_teardown:
        module.teardown = AsyncMock()  # type: ignore[attr-defined]
    if has_health:
        module.health = MagicMock(return_value=True)  # type: ignore[attr-defined]

    api = MagicMock()
    instance = PluginInstance(
        manifest=_make_manifest(name),
        module=module,
        api=api,
        status=status,
    )
    return instance


@pytest.fixture
def registry() -> PluginRegistry:
    return PluginRegistry()


@pytest.fixture
def sandbox() -> PluginSandbox:
    return PluginSandbox(default_timeout_s=5.0)


@pytest.fixture
def lifecycle(registry: PluginRegistry, sandbox: PluginSandbox) -> PluginLifecycleManager:
    return PluginLifecycleManager(
        registry=registry,
        sandbox=sandbox,
        health_check_interval_s=1,
        max_consecutive_failures=3,
    )


class TestStartup:
    async def test_startup_calls_setup(self, lifecycle: PluginLifecycleManager) -> None:
        """Startup invokes module.setup() via sandbox."""
        plugin = _make_plugin()
        await lifecycle.startup(plugin)
        assert plugin.status == "active"
        assert plugin.consecutive_failures == 0

    async def test_startup_skip_no_module(self, lifecycle: PluginLifecycleManager) -> None:
        """Startup skips gracefully when module is None."""
        plugin = _make_plugin()
        plugin.module = None
        await lifecycle.startup(plugin)
        # Status unchanged since startup was skipped
        assert plugin.status == "active"


class TestShutdown:
    async def test_shutdown_calls_teardown(self, lifecycle: PluginLifecycleManager) -> None:
        """Calls module.teardown() if defined."""
        plugin = _make_plugin()
        await lifecycle.shutdown(plugin)
        assert plugin.status == "inactive"

    async def test_shutdown_no_teardown(self, lifecycle: PluginLifecycleManager) -> None:
        """Gracefully handles module without teardown()."""
        plugin = _make_plugin(has_teardown=False)
        await lifecycle.shutdown(plugin)
        assert plugin.status == "inactive"

    async def test_shutdown_teardown_error(self, lifecycle: PluginLifecycleManager) -> None:
        """Teardown error is caught, plugin still marked inactive."""
        plugin = _make_plugin()
        plugin.module.teardown = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[union-attr]
        await lifecycle.shutdown(plugin)
        assert plugin.status == "inactive"


class TestRestart:
    async def test_restart_cycles(self, lifecycle: PluginLifecycleManager) -> None:
        """Shutdown then startup in sequence."""
        plugin = _make_plugin()
        plugin.status = "degraded"
        await lifecycle.restart(plugin)
        assert plugin.status == "active"
        assert plugin.consecutive_failures == 0


class TestHealthCheck:
    async def test_health_check_auto_disable(
        self,
        lifecycle: PluginLifecycleManager,
        registry: PluginRegistry,
    ) -> None:
        """3 consecutive failures disables plugin."""
        plugin = _make_plugin(has_health=True)
        plugin.module.health = MagicMock(side_effect=RuntimeError("fail"))  # type: ignore[union-attr]
        # Register plugin so disable() works
        registry._plugins["test-plugin"] = plugin

        for _ in range(3):
            await lifecycle.check_health(plugin)

        assert plugin.status == "disabled"

    async def test_health_check_recovery(self, lifecycle: PluginLifecycleManager) -> None:
        """Unhealthy -> healthy resets counter."""
        plugin = _make_plugin(has_health=True)
        plugin.status = "degraded"
        plugin.consecutive_failures = 2
        # health() returns True -> healthy
        plugin.module.health = MagicMock(return_value=True)  # type: ignore[union-attr]

        await lifecycle.check_health(plugin)

        assert plugin.consecutive_failures == 0
        assert plugin.status == "active"

    async def test_check_all_health(
        self,
        lifecycle: PluginLifecycleManager,
        registry: PluginRegistry,
    ) -> None:
        """Iterates active plugins only."""
        active = _make_plugin("active-plugin", status="active", has_health=True)
        disabled = _make_plugin("disabled-plugin", status="disabled", has_health=True)
        registry._plugins["active-plugin"] = active
        registry._plugins["disabled-plugin"] = disabled

        await lifecycle.check_all_health()
        # Active plugin should have been checked (health returns True = healthy)
        assert active.consecutive_failures == 0
        # Disabled plugin should be skipped
        assert disabled.status == "disabled"

    async def test_health_skip_inactive(self, lifecycle: PluginLifecycleManager) -> None:
        """Inactive plugins are not health-checked."""
        plugin = _make_plugin(has_health=True)
        plugin.status = "inactive"
        await lifecycle.check_health(plugin)
        # No changes since health check was skipped
        assert plugin.consecutive_failures == 0


class TestHealthMonitor:
    async def test_start_stop_health_monitor(self, lifecycle: PluginLifecycleManager) -> None:
        """Background task starts and cancels cleanly."""
        lifecycle.start_health_monitor()
        assert lifecycle._health_task is not None
        assert not lifecycle._health_task.done()

        await lifecycle.stop_health_monitor()
        assert lifecycle._health_task is None

    async def test_start_health_monitor_idempotent(self, lifecycle: PluginLifecycleManager) -> None:
        """Starting twice doesn't create a second task."""
        lifecycle.start_health_monitor()
        task1 = lifecycle._health_task
        lifecycle.start_health_monitor()
        assert lifecycle._health_task is task1
        await lifecycle.stop_health_monitor()


class TestShutdownAll:
    async def test_shutdown_all(
        self,
        lifecycle: PluginLifecycleManager,
        registry: PluginRegistry,
    ) -> None:
        """Stops monitor + shuts down all active plugins."""
        active = _make_plugin("p1", status="active")
        degraded = _make_plugin("p2", status="degraded")
        inactive = _make_plugin("p3", status="inactive")
        registry._plugins["p1"] = active
        registry._plugins["p2"] = degraded
        registry._plugins["p3"] = inactive

        lifecycle.start_health_monitor()
        await lifecycle.shutdown_all()

        assert lifecycle._health_task is None
        assert active.status == "inactive"
        assert degraded.status == "inactive"
        assert inactive.status == "inactive"  # was already inactive
