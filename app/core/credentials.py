"""Credential pool with round-robin rotation and automatic cooldowns.

Manages multiple API keys per service with health tracking, exponential
backoff cooldowns, and Redis-backed state (in-memory fallback when Redis
is unavailable).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Any

from app.core.config import CredentialsConfig
from app.core.exceptions import NoHealthyCredentialsError, ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Status codes that trigger immediate cooldown
_COOLDOWN_TRIGGER_CODES: frozenset[int] = frozenset({429, 401, 403})

# 51.1 — agent revocation. Redis key holds JSON {reason, revoked_at, ttl_s}.
_REVOCATION_KEY_PREFIX = "credentials:revoked:"


class CredentialRevokedError(ServiceUnavailableError):
    """Agent's credentials have been revoked by an admin or kill switch (503)."""

    def __init__(self, agent_id: str, reason: str) -> None:
        self.agent_id = agent_id
        self.reason = reason
        super().__init__(f"Credentials revoked for agent '{agent_id}': {reason}")


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


def _get_hmac_salt() -> bytes:
    """Return the app secret for HMAC key hashing. Falls back to a static salt."""
    try:
        from app.core.config import get_settings

        return get_settings().auth.jwt_secret_key.encode()
    except Exception:
        return b"credential-pool-default-salt"


def _hash_key(key: str, *, salt: bytes | None = None) -> str:
    """Return a short HMAC-SHA256 prefix for safe key identification.

    Uses the app secret as HMAC key so hashes cannot be brute-forced
    without knowing the secret, even if an attacker has candidate keys.
    """
    hmac_salt = salt if salt is not None else _get_hmac_salt()
    return hmac.new(hmac_salt, key.encode(), hashlib.sha256).hexdigest()[:12]


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

    async def get_key(self, *, agent_id: str | None = None) -> CredentialLease:
        """Return the next healthy key via round-robin.

        When ``agent_id`` is provided, the agent's revocation state is checked
        (51.1) before any round-robin selection — opt-in for callers that have
        an agent identity. Existing call sites without an identity bypass the
        check and behave as before.

        Raises:
            CredentialRevokedError: When ``agent_id`` is set and the agent has
                been revoked via :func:`revoke_for_agent`.
            NoHealthyCredentialsError: When no healthy keys are available.
        """
        if agent_id is not None:
            revocation = await _get_revocation(agent_id)
            if revocation is not None:
                logger.warning(
                    "credentials.lease_blocked_revoked",
                    service=self._service,
                    agent_id=agent_id,
                    reason=revocation.get("reason", ""),
                )
                raise CredentialRevokedError(agent_id, str(revocation.get("reason", "")))
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

    async def pool_status(self) -> dict[str, Any]:
        """Return health summary for this pool. Key values never exposed."""
        keys_status: list[dict[str, Any]] = []
        healthy_count = 0
        cooled_down_count = 0
        unhealthy_count = 0
        now = time.monotonic()

        for kh in self._key_hashes:
            state = await self._get_state(kh)
            if not state.healthy:
                unhealthy_count += 1
                status = "unhealthy"
            elif state.cooldown_until > now:
                cooled_down_count += 1
                status = "cooled_down"
            else:
                healthy_count += 1
                status = "healthy"
            keys_status.append(
                {
                    "key_hash": kh,
                    "status": status,
                    "failure_count": state.failure_count,
                    "last_failure_code": state.last_failure_code or None,
                    "cooldown_remaining_s": max(0, round(state.cooldown_until - now, 1))
                    if state.cooldown_until > now
                    else 0,
                }
            )

        return {
            "service": self._service,
            "key_count": len(self._key_hashes),
            "healthy": healthy_count,
            "cooled_down": cooled_down_count,
            "unhealthy": unhealthy_count,
            "keys": keys_status,
        }


# ── Agent Revocation (51.1) ──
#
# Revocation is global per-agent (not per-pool): every pool's ``get_key``
# consults the same Redis key, so a single ``revoke_for_agent`` call blocks
# all future leases across replicas. In-flight leases that already hold a
# key are unaffected — they complete naturally; the agent simply cannot
# obtain a new lease until restored or the TTL elapses.

_revocation_fallback: dict[str, dict[str, Any]] = {}


async def _get_revocation(agent_id: str) -> dict[str, Any] | None:
    """Return the revocation record for ``agent_id`` if revoked, else ``None``."""
    try:
        from app.core.redis import get_redis

        r = await get_redis()
        raw = await r.get(f"{_REVOCATION_KEY_PREFIX}{agent_id}")
        if raw is None:
            return None
        data: dict[str, Any] = json.loads(raw)
        return data
    except Exception:
        return _revocation_fallback.get(agent_id)


async def is_revoked(agent_id: str) -> bool:
    """Check whether ``agent_id`` is currently revoked."""
    return (await _get_revocation(agent_id)) is not None


async def revoke_for_agent(
    agent_id: str,
    reason: str,
    *,
    ttl: int | None = None,
) -> None:
    """Revoke all future credential leases for ``agent_id``.

    ``ttl`` is the revocation lifetime in seconds. ``None`` means use the
    configured default (``settings.security.revocation_default_ttl_s``); if
    that is also ``None`` the revocation is permanent until restored via
    :func:`restore_for_agent` or the admin endpoint.

    Idempotent: a second call replaces the existing record (useful for
    extending a TTL or updating ``reason``).
    """
    effective_ttl: int | None = ttl
    if effective_ttl is None:
        try:
            from app.core.config import get_settings

            effective_ttl = get_settings().security.revocation_default_ttl_s
        except Exception:
            effective_ttl = None

    record: dict[str, Any] = {
        "reason": reason,
        "revoked_at": time.time(),
        "ttl_s": effective_ttl,
    }
    payload = json.dumps(record)
    redis_key = f"{_REVOCATION_KEY_PREFIX}{agent_id}"
    redis_persisted = False
    try:
        from app.core.redis import get_redis

        r = await get_redis()
        if effective_ttl is not None and effective_ttl > 0:
            await r.setex(redis_key, effective_ttl, payload)
        else:
            await r.set(redis_key, payload)
        redis_persisted = True
    except Exception:
        _revocation_fallback[agent_id] = record

    logger.warning(
        "credentials.revoked_for_agent",
        agent_id=agent_id,
        reason=reason,
        ttl_s=effective_ttl,
        redis_persisted=redis_persisted,
    )


async def restore_for_agent(agent_id: str) -> bool:
    """Lift a revocation. Returns ``True`` if the agent was previously revoked."""
    was_revoked = False
    try:
        from app.core.redis import get_redis

        r = await get_redis()
        deleted = await r.delete(f"{_REVOCATION_KEY_PREFIX}{agent_id}")
        was_revoked = bool(deleted)
    except Exception as exc:
        # Redis unreachable — fall through to in-memory fallback below.
        logger.debug("credentials.restore_redis_unavailable", agent_id=agent_id, error=str(exc))

    if agent_id in _revocation_fallback:
        del _revocation_fallback[agent_id]
        was_revoked = True

    if was_revoked:
        logger.info("credentials.restored_for_agent", agent_id=agent_id)
    return was_revoked


def reset_revocations() -> None:
    """Clear in-memory revocation fallback. Test-only — does not touch Redis."""
    _revocation_fallback.clear()


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


def initialize_pools() -> None:
    """Eagerly create pools for all configured services at startup."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.credentials.enabled:
        return
    for service, keys in settings.credentials.pools.items():
        if keys and service not in _pools:
            _pools[service] = CredentialPool(service, keys, settings.credentials)
            logger.info("credentials.pool_initialized", service=service, key_count=len(keys))


def get_all_pools() -> MappingProxyType[str, CredentialPool]:
    """Return all registered credential pools (frozen read-only view).

    Callers can iterate and call pool_status() but cannot mutate
    the registry or access raw keys via get_key().
    """
    return MappingProxyType(_pools)


def reset_pools() -> None:
    """Clear all pools. For testing only."""
    _pools.clear()
