"""Credential pool with round-robin rotation and automatic cooldowns.

Manages multiple API keys per service with health tracking, exponential
backoff cooldowns, and Redis-backed state (in-memory fallback when Redis
is unavailable).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.config import CredentialsConfig
from app.core.exceptions import NoHealthyCredentialsError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Status codes that trigger immediate cooldown
_COOLDOWN_TRIGGER_CODES: frozenset[int] = frozenset({429, 401, 403})


@dataclass
class _KeyState:
    """Per-key health state."""

    healthy: bool = True
    cooldown_until: float = 0.0  # time.monotonic() timestamp
    failure_count: int = 0
    last_failure_code: int = 0


@dataclass
class CredentialLease:
    """Handle to a borrowed credential key."""

    service: str
    key: str
    key_hash: str
    _pool: CredentialPool = field(repr=False)

    async def report_success(self) -> None:
        """Reset failure state for this key."""
        await self._pool._record_success(self.key_hash)

    async def report_failure(self, status_code: int) -> None:
        """Record a failure against this key."""
        await self._pool._record_failure(self.key_hash, status_code)


def _hash_key(key: str) -> str:
    """Return a short SHA-256 prefix for safe logging."""
    return hashlib.sha256(key.encode()).hexdigest()[:12]


class CredentialPool:
    """Manages keys for a single service with rotation and cooldowns."""

    def __init__(
        self,
        service: str,
        keys: list[str],
        config: CredentialsConfig,
    ) -> None:
        self._service = service
        self._keys = keys
        self._key_hashes = [_hash_key(k) for k in keys]
        self._config = config
        self._index = 0
        self._lock = asyncio.Lock()
        self._fallback: dict[str, _KeyState] = {}

    async def get_key(self) -> CredentialLease:
        """Return the next healthy key via round-robin.

        Raises:
            NoHealthyCredentialsError: When no healthy keys are available.
        """
        async with self._lock:
            n = len(self._keys)
            for _ in range(n):
                idx = self._index % n
                self._index = idx + 1
                key = self._keys[idx]
                key_hash = self._key_hashes[idx]
                state = await self._get_state(key_hash)

                now = time.monotonic()
                if not state.healthy:
                    continue
                if state.cooldown_until > now:
                    continue

                logger.debug(
                    "credentials.lease_issued",
                    service=self._service,
                    key_hash=key_hash,
                )
                return CredentialLease(
                    service=self._service,
                    key=key,
                    key_hash=key_hash,
                    _pool=self,
                )

            # Wrapped all the way around — no healthy key found
            logger.warning(
                "credentials.pool_exhausted",
                service=self._service,
                total_keys=n,
            )
            raise NoHealthyCredentialsError(self._service)

    async def _get_state(self, key_hash: str) -> _KeyState:
        """Load key state from Redis, fall back to in-memory."""
        try:
            from app.core.redis import get_redis

            r = await get_redis()
            raw = await r.get(f"credentials:{self._service}:{key_hash}")
            if raw is None:
                return _KeyState()
            data = json.loads(raw)
            return _KeyState(**data)
        except Exception:
            return self._fallback.get(key_hash, _KeyState())

    async def _set_state(self, key_hash: str, state: _KeyState) -> None:
        """Persist key state to Redis with TTL, fall back to in-memory."""
        try:
            from app.core.redis import get_redis

            r = await get_redis()
            await r.setex(
                f"credentials:{self._service}:{key_hash}",
                self._config.unhealthy_ttl_seconds,
                json.dumps(asdict(state)),
            )
        except Exception:
            self._fallback[key_hash] = state

    async def _record_success(self, key_hash: str) -> None:
        """Reset failure count and cooldown for a key."""
        state = _KeyState(healthy=True, cooldown_until=0.0, failure_count=0, last_failure_code=0)
        await self._set_state(key_hash, state)
        logger.debug("credentials.success_recorded", service=self._service, key_hash=key_hash)

    async def _record_failure(self, key_hash: str, status_code: int) -> None:
        """Record failure. Trigger cooldown on 429/401/403, mark unhealthy at threshold."""
        state = await self._get_state(key_hash)
        state.failure_count += 1
        state.last_failure_code = status_code

        if status_code in _COOLDOWN_TRIGGER_CODES:
            backoff = min(
                self._config.cooldown_initial_seconds * (2 ** (state.failure_count - 1)),
                self._config.cooldown_max_seconds,
            )
            state.cooldown_until = time.monotonic() + backoff
            logger.info(
                "credentials.cooldown_entered",
                service=self._service,
                key_hash=key_hash,
                status_code=status_code,
                backoff_seconds=backoff,
            )

        if state.failure_count >= self._config.failure_threshold:
            state.healthy = False
            logger.warning(
                "credentials.key_unhealthy",
                service=self._service,
                key_hash=key_hash,
                failure_count=state.failure_count,
            )

        await self._set_state(key_hash, state)

    def pool_status(self) -> dict[str, Any]:
        """Synchronous snapshot for health check API (future 46.4)."""
        return {
            "service": self._service,
            "total_keys": len(self._keys),
            "key_hashes": list(self._key_hashes),
        }


# ── Singleton Pool Registry ──

_pools: dict[str, CredentialPool] = {}


def get_credential_pool(service: str) -> CredentialPool:
    """Get or create a CredentialPool for the given service."""
    if service not in _pools:
        from app.core.config import get_settings

        settings = get_settings()
        keys = settings.credentials.pools.get(service, [])
        if not keys:
            raise NoHealthyCredentialsError(service)
        _pools[service] = CredentialPool(service, keys, settings.credentials)
    return _pools[service]


def reset_pools() -> None:
    """Clear all pools. For testing only."""
    _pools.clear()
