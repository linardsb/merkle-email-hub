"""Runtime SKILL.md content override for A/B testing and prompt store.

Priority: prompt store (DB) > in-memory override > SKILL.md on disk.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_overrides: dict[str, str] = {}

# Cache for prompt store lookups (populated by preload_prompt_store_cache)
_store_cache: dict[str, str] = {}


def set_override(agent: str, content: str) -> None:
    """Set SKILL.md content override for an agent."""
    _overrides[agent] = content


def clear_override(agent: str) -> None:
    """Remove SKILL.md content override for an agent."""
    _overrides.pop(agent, None)


def clear_all_overrides() -> None:
    """Remove all overrides (cleanup after A/B test)."""
    _overrides.clear()


def set_store_cache(agent: str, content: str) -> None:
    """Cache a prompt store lookup result."""
    _store_cache[agent] = content


def clear_store_cache(agent: str | None = None) -> None:
    """Clear prompt store cache (all or specific agent)."""
    if agent is None:
        _store_cache.clear()
    else:
        _store_cache.pop(agent, None)


def get_override(agent: str) -> str | None:
    """Get prompt override for an agent.

    Priority: prompt store cache > in-memory A/B override > None (use SKILL.md).
    Prompt store is only checked when AI__PROMPT_STORE_ENABLED=true.
    """
    settings = get_settings()
    if settings.ai.prompt_store_enabled and agent in _store_cache:
        return _store_cache[agent]
    return _overrides.get(agent)
