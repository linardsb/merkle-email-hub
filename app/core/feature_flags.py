"""Redis-backed feature flags.

Lightweight feature flag system using Redis for shared state across workers.
Flags can be toggled at runtime without redeployment.

Usage:
    flags = FeatureFlags(prefix="myapp")

    # Set a flag
    await flags.enable("dark_mode")
    await flags.disable("dark_mode")

    # Check a flag
    if await flags.is_enabled("dark_mode"):
        ...

    # Check with default (when Redis is unavailable)
    if await flags.is_enabled("beta_feature", default=False):
        ...
"""

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)


class FeatureFlags:
    """Redis-backed feature flag manager."""

    def __init__(self, prefix: str = "flags") -> None:
        self.prefix = prefix

    def _key(self, flag: str) -> str:
        return f"{self.prefix}:{flag}"

    async def is_enabled(self, flag: str, *, default: bool = False) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag: The flag name.
            default: Value to return if Redis is unavailable or flag is not set.

        Returns:
            True if the flag is enabled, False otherwise.
        """
        try:
            redis = await get_redis()
            value = await redis.get(self._key(flag))
            if value is None:
                return default
            return bool(value == "1")
        except Exception:
            logger.warning("feature_flags.check_failed", flag=flag, default=default)
            return default

    async def enable(self, flag: str) -> None:
        """Enable a feature flag."""
        try:
            redis = await get_redis()
            await redis.set(self._key(flag), "1")
            logger.info("feature_flags.enabled", flag=flag)
        except Exception:
            logger.error("feature_flags.enable_failed", flag=flag)

    async def disable(self, flag: str) -> None:
        """Disable a feature flag."""
        try:
            redis = await get_redis()
            await redis.set(self._key(flag), "0")
            logger.info("feature_flags.disabled", flag=flag)
        except Exception:
            logger.error("feature_flags.disable_failed", flag=flag)

    async def delete(self, flag: str) -> None:
        """Remove a feature flag entirely."""
        try:
            redis = await get_redis()
            await redis.delete(self._key(flag))
        except Exception:
            logger.error("feature_flags.delete_failed", flag=flag)

    async def list_all(self) -> dict[str, bool]:
        """List all feature flags and their states."""
        try:
            redis = await get_redis()
            keys: list[str] = []
            async for key in redis.scan_iter(f"{self.prefix}:*"):  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                keys.append(str(key))  # pyright: ignore[reportUnknownArgumentType]
            if not keys:
                return {}
            values = await redis.mget(*keys)  # pyright: ignore[reportUnknownArgumentType]
            return {
                str(k).removeprefix(f"{self.prefix}:"): v == "1"
                for k, v in zip(keys, values, strict=False)  # pyright: ignore[reportUnknownArgumentType]
                if v is not None
            }
        except Exception:
            logger.error("feature_flags.list_failed")
            return {}
