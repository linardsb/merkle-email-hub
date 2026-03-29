"""Plugin lifecycle management — startup, shutdown, health monitoring."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.plugins.sandbox import PluginSandbox

if TYPE_CHECKING:
    from app.plugins.registry import PluginInstance, PluginRegistry

logger = get_logger(__name__)


class PluginLifecycleManager:
    """Manages plugin startup, shutdown, and periodic health checks."""

    def __init__(
        self,
        registry: PluginRegistry,
        sandbox: PluginSandbox,
        health_check_interval_s: int = 60,
        max_consecutive_failures: int = 3,
    ) -> None:
        self._registry = registry
        self._sandbox = sandbox
        self._health_check_interval_s = health_check_interval_s
        self._max_consecutive_failures = max_consecutive_failures
        self._health_task: asyncio.Task[None] | None = None

    async def startup(self, plugin: PluginInstance) -> None:
        """Call plugin's setup() and mark as active.

        setup() was already called during load_and_register().
        This method is for explicit lifecycle management (e.g., restart).
        """
        if plugin.module is None:
            logger.warning("plugins.startup_skip_no_module", plugin=plugin.manifest.name)
            return

        setup_fn = getattr(plugin.module, "setup", None)
        if setup_fn is not None:
            await self._sandbox.execute(plugin.manifest.name, setup_fn, plugin.api, timeout_s=30.0)
        plugin.status = "active"
        plugin.consecutive_failures = 0
        logger.info("plugins.lifecycle_started", plugin=plugin.manifest.name)

    async def shutdown(self, plugin: PluginInstance) -> None:
        """Call plugin's teardown() if defined, mark inactive."""
        if plugin.module is None:
            return

        teardown_fn = getattr(plugin.module, "teardown", None)
        if teardown_fn is not None:
            try:
                await self._sandbox.execute(plugin.manifest.name, teardown_fn, timeout_s=10.0)
            except Exception:
                logger.warning(
                    "plugins.teardown_error",
                    plugin=plugin.manifest.name,
                    exc_info=True,
                )
        plugin.status = "inactive"
        logger.info("plugins.lifecycle_stopped", plugin=plugin.manifest.name)

    async def restart(self, plugin: PluginInstance) -> None:
        """Shutdown, then startup (for hot reload)."""
        await self.shutdown(plugin)
        await self.startup(plugin)
        logger.info("plugins.lifecycle_restarted", plugin=plugin.manifest.name)

    async def check_health(self, plugin: PluginInstance) -> None:
        """Run health check on a single plugin. Auto-disable after consecutive failures."""
        if plugin.module is None or plugin.status not in ("active", "degraded"):
            return

        health_fn = getattr(plugin.module, "health", None)
        result = await self._sandbox.health_check(plugin.manifest.name, health_fn)

        if result.status == "healthy":
            plugin.consecutive_failures = 0
            if plugin.status == "degraded":
                plugin.status = "active"
                logger.info("plugins.health_recovered", plugin=plugin.manifest.name)
        elif result.status == "degraded":
            plugin.status = "degraded"
            logger.warning(
                "plugins.health_degraded",
                plugin=plugin.manifest.name,
                message=result.message,
            )
        else:  # unhealthy
            plugin.consecutive_failures += 1
            logger.warning(
                "plugins.health_unhealthy",
                plugin=plugin.manifest.name,
                message=result.message,
                consecutive_failures=plugin.consecutive_failures,
            )
            if plugin.consecutive_failures >= self._max_consecutive_failures:
                self._registry.disable(plugin.manifest.name)
                logger.error(
                    "plugins.health_auto_disabled",
                    plugin=plugin.manifest.name,
                    failures=plugin.consecutive_failures,
                )

    async def check_all_health(self) -> None:
        """Run health checks on all active/degraded plugins."""
        for instance in self._registry.list_plugins():
            if instance.status in ("active", "degraded"):
                await self.check_health(instance)

    def start_health_monitor(self) -> None:
        """Start the periodic health check background task."""
        if self._health_task is not None:
            return
        self._health_task = asyncio.create_task(self._health_loop())
        logger.info(
            "plugins.health_monitor_started",
            interval_s=self._health_check_interval_s,
        )

    async def _health_loop(self) -> None:
        """Background loop that periodically checks plugin health."""
        while True:
            await asyncio.sleep(self._health_check_interval_s)
            try:
                await self.check_all_health()
            except Exception:
                logger.warning("plugins.health_loop_error", exc_info=True)

    async def stop_health_monitor(self) -> None:
        """Stop the periodic health check background task."""
        if self._health_task is not None:
            self._health_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_task
            self._health_task = None
            logger.info("plugins.health_monitor_stopped")

    async def shutdown_all(self) -> None:
        """Gracefully shut down all active plugins and stop health monitor."""
        await self.stop_health_monitor()
        for instance in self._registry.list_plugins():
            if instance.status in ("active", "degraded"):
                await self.shutdown(instance)
