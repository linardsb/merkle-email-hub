"""Tests for plugin execution sandbox."""

from __future__ import annotations

import asyncio

import pytest

from app.plugins.exceptions import PluginError, PluginTimeoutError
from app.plugins.sandbox import PluginSandbox, make_plugin_context


@pytest.fixture
def sandbox() -> PluginSandbox:
    return PluginSandbox(default_timeout_s=2.0)


class TestSandboxExecute:
    async def test_execute_success(self, sandbox: PluginSandbox) -> None:
        """Async function completes, result returned."""

        async def add(a: int, b: int) -> int:
            return a + b

        result = await sandbox.execute("test-plugin", add, 2, 3)
        assert result == 5

    async def test_execute_timeout(self, sandbox: PluginSandbox) -> None:
        """Function that sleeps forever raises PluginTimeoutError."""

        async def hang() -> None:
            await asyncio.sleep(100)

        with pytest.raises(PluginTimeoutError, match="timed out"):
            await sandbox.execute("test-plugin", hang, timeout_s=0.1)

    async def test_execute_error_isolation(self, sandbox: PluginSandbox) -> None:
        """Function raising ValueError is wrapped as PluginError."""

        async def fail() -> None:
            msg = "bad input"
            raise ValueError(msg)

        with pytest.raises(PluginError, match="ValueError"):
            await sandbox.execute("test-plugin", fail)

    async def test_execute_sync_function(self, sandbox: PluginSandbox) -> None:
        """Sync callable works via _call()."""

        def multiply(a: int, b: int) -> int:
            return a * b

        result = await sandbox.execute("test-plugin", multiply, 3, 4)
        assert result == 12

    async def test_execute_custom_timeout(self, sandbox: PluginSandbox) -> None:
        """Custom timeout_s overrides default."""

        async def quick() -> str:
            return "done"

        result = await sandbox.execute("test-plugin", quick, timeout_s=10.0)
        assert result == "done"

    async def test_execute_plugin_error_not_double_wrapped(self, sandbox: PluginSandbox) -> None:
        """PluginTimeoutError is re-raised without wrapping."""

        async def raise_timeout() -> None:
            raise PluginTimeoutError("already timed out")

        with pytest.raises(PluginTimeoutError, match="already timed out"):
            await sandbox.execute("test-plugin", raise_timeout)


class TestHealthCheck:
    async def test_health_check_healthy(self, sandbox: PluginSandbox) -> None:
        """Plugin returning True yields healthy status."""

        def healthy() -> bool:
            return True

        result = await sandbox.health_check("test-plugin", healthy)
        assert result.status == "healthy"
        assert result.latency_ms >= 0

    async def test_health_check_dict_response(self, sandbox: PluginSandbox) -> None:
        """Plugin returning dict with status/message."""

        def degraded() -> dict[str, str]:
            return {"status": "degraded", "message": "High memory usage"}

        result = await sandbox.health_check("test-plugin", degraded)
        assert result.status == "degraded"
        assert result.message == "High memory usage"

    async def test_health_check_no_function(self, sandbox: PluginSandbox) -> None:
        """None health_fn returns optimistic healthy."""
        result = await sandbox.health_check("test-plugin", None)
        assert result.status == "healthy"
        assert result.message == "No health check defined"

    async def test_health_check_timeout(self, sandbox: PluginSandbox) -> None:
        """Health function that hangs yields unhealthy."""

        async def hang() -> None:
            await asyncio.sleep(100)

        result = await sandbox.health_check("test-plugin", hang)
        assert result.status == "unhealthy"
        assert "timed out" in (result.message or "")

    async def test_health_check_exception(self, sandbox: PluginSandbox) -> None:
        """Health function raising exception yields unhealthy with message."""

        def broken() -> None:
            msg = "connection refused"
            raise ConnectionError(msg)

        result = await sandbox.health_check("test-plugin", broken)
        assert result.status == "unhealthy"
        assert "ConnectionError" in (result.message or "")

    async def test_health_check_bool_false(self, sandbox: PluginSandbox) -> None:
        """Plugin returning False yields unhealthy."""

        def unhealthy() -> bool:
            return False

        result = await sandbox.health_check("test-plugin", unhealthy)
        assert result.status == "unhealthy"


class TestMakePluginContext:
    def test_make_plugin_context(self) -> None:
        """Creates context with logger and config."""
        ctx = make_plugin_context("my-plugin", {"key": "value"})
        assert ctx.plugin_name == "my-plugin"
        assert ctx.config == {"key": "value"}
        assert ctx.logger is not None

    def test_make_plugin_context_default_config(self) -> None:
        """Default config is empty dict."""
        ctx = make_plugin_context("my-plugin")
        assert ctx.config == {}
