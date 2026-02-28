"""Circuit breaker for external API calls.

Prevents cascading failures when an external service is down by failing
fast after a threshold of consecutive errors. Automatically retries after
a configurable reset timeout.

Usage:
    breaker = CircuitBreaker(name="weather-api", failure_threshold=5, reset_timeout=30)

    async def get_weather():
        async with breaker:
            return await httpx.get("https://api.weather.com/current")

States:
    CLOSED: Normal operation, requests pass through
    OPEN: Requests fail immediately (circuit tripped)
    HALF_OPEN: Single test request allowed to check recovery
"""

import asyncio
import time
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    pass


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state, accounting for timeout transitions."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.reset_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    async def __aenter__(self) -> "CircuitBreaker":
        async with self._lock:
            current = self.state
            if current == CircuitState.OPEN:
                logger.warning(
                    f"circuit_breaker.{self.name}.rejected",
                    state="open",
                    failures=self._failure_count,
                )
                raise CircuitOpenError(f"Circuit breaker '{self.name}' is open")

            if current == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitOpenError(f"Circuit breaker '{self.name}' half-open limit reached")
                self._half_open_calls += 1

        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        async with self._lock:
            if exc_type is None:
                # Success
                if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                    logger.info(f"circuit_breaker.{self.name}.recovered")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_calls = 0
            else:
                # Failure
                self._failure_count += 1
                self._last_failure_time = time.monotonic()

                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._half_open_calls = 0
                    logger.error(
                        f"circuit_breaker.{self.name}.opened",
                        failures=self._failure_count,
                        reset_timeout=self.reset_timeout,
                    )

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
