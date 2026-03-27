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


def set_override_from_version(agent: str, skill_name: str, version: str) -> None:
    """Load SKILL.md content from a specific version and set as override.

    Used for A/B testing version X vs version Y without changing disk files.
    Loads the versioned content via ``git show`` and installs it as the
    active in-memory override for *agent*.
    """
    from app.ai.agents.skill_version import (
        git_show_content,
        load_manifest,
        resolve_skill_path,
    )

    manifest = load_manifest(agent)
    if manifest is None:
        msg = f"No skill-versions.yaml for agent: {agent}"
        raise ValueError(msg)

    cfg = manifest.skills.get(skill_name)
    if cfg is None:
        msg = f"Skill {skill_name!r} not in manifest for {agent}"
        raise ValueError(msg)

    entry = cfg.versions.get(version)
    if entry is None:
        msg = f"Version {version!r} not found for {agent}/{skill_name}"
        raise ValueError(msg)

    path = resolve_skill_path(agent, skill_name)
    content = git_show_content(entry.hash, path)
    set_override(agent, content)
    logger.info(
        "skill_override.set_from_version",
        agent=agent,
        skill=skill_name,
        version=version,
    )


def get_override(agent: str) -> str | None:
    """Get prompt override for an agent.

    Priority: prompt store cache > in-memory A/B override > None (use SKILL.md).
    Prompt store is only checked when AI__PROMPT_STORE_ENABLED=true.
    """
    settings = get_settings()
    if settings.ai.prompt_store_enabled and agent in _store_cache:
        return _store_cache[agent]
    return _overrides.get(agent)
