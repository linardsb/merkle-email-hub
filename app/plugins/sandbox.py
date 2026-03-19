"""Plugin execution sandbox with timeout, error isolation, and resource tracking."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.plugins.exceptions import PluginError, PluginTimeoutError

logger = get_logger(__name__)


@dataclass(frozen=True)
class PluginHealth:
    """Result of a plugin health check."""

    status: str  # healthy, degraded, unhealthy
    message: str | None = None
    latency_ms: float = 0.0


@dataclass
class PluginExecutionContext:
    """Context passed to every sandboxed plugin function call."""

    logger: Any
    config: dict[str, Any] = field(default_factory=dict)
    plugin_name: str = ""


class PluginSandbox:
    """Executes plugin functions with timeout and error isolation."""

    def __init__(self, default_timeout_s: float = 30.0) -> None:
        self._default_timeout_s = default_timeout_s

    async def execute(
        self,
        plugin_name: str,
        fn: Callable[..., Any],
        *args: object,
        timeout_s: float | None = None,
        **kwargs: object,
    ) -> object:
        """Run a plugin function with timeout and error isolation.

        Returns the function result on success.
        Raises PluginTimeoutError on timeout, PluginError on any other failure.
        """
        effective_timeout = timeout_s if timeout_s is not None else self._default_timeout_s
        start = time.monotonic()

        try:
            result = await asyncio.wait_for(
                self._call(fn, *args, **kwargs),
                timeout=effective_timeout,
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "plugins.execute_completed",
                plugin=plugin_name,
                elapsed_ms=round(elapsed_ms, 2),
            )
            return result
        except TimeoutError:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "plugins.execute_timeout",
                plugin=plugin_name,
                timeout_s=effective_timeout,
                elapsed_ms=round(elapsed_ms, 2),
            )
            raise PluginTimeoutError(
                f"Plugin '{plugin_name}' timed out after {effective_timeout}s"
            ) from None
        except PluginTimeoutError:
            raise  # Don't double-wrap
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "plugins.execute_error",
                plugin=plugin_name,
                error=str(exc),
                error_type=type(exc).__name__,
                elapsed_ms=round(elapsed_ms, 2),
            )
            raise PluginError(f"Plugin '{plugin_name}' raised {type(exc).__name__}: {exc}") from exc

    async def _call(self, fn: Callable[..., Any], *args: object, **kwargs: object) -> object:
        """Call a function, handling both sync and async callables."""
        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def health_check(
        self,
        plugin_name: str,  # noqa: ARG002
        health_fn: Callable[..., Any] | None,
    ) -> PluginHealth:
        """Call a plugin's health() function if defined.

        Returns PluginHealth with status healthy/degraded/unhealthy.
        If no health function is defined, returns healthy (optimistic).
        """
        if health_fn is None:
            return PluginHealth(status="healthy", message="No health check defined")

        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                self._call(health_fn),
                timeout=5.0,
            )
            latency_ms = (time.monotonic() - start) * 1000

            # Plugin can return a dict with status/message or just a bool
            if isinstance(result, dict):
                return PluginHealth(
                    status=result.get("status", "healthy"),
                    message=result.get("message"),
                    latency_ms=round(latency_ms, 2),
                )
            if isinstance(result, bool):
                return PluginHealth(
                    status="healthy" if result else "unhealthy",
                    latency_ms=round(latency_ms, 2),
                )
            return PluginHealth(status="healthy", latency_ms=round(latency_ms, 2))
        except TimeoutError:
            latency_ms = (time.monotonic() - start) * 1000
            return PluginHealth(
                status="unhealthy",
                message="Health check timed out after 5s",
                latency_ms=round(latency_ms, 2),
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            return PluginHealth(
                status="unhealthy",
                message=f"{type(exc).__name__}: {exc}",
                latency_ms=round(latency_ms, 2),
            )


def make_plugin_context(
    plugin_name: str,
    config: dict[str, Any] | None = None,
) -> PluginExecutionContext:
    """Create an execution context for a plugin."""
    return PluginExecutionContext(
        logger=get_logger(f"plugin.{plugin_name}"),
        config=config or {},
        plugin_name=plugin_name,
    )
