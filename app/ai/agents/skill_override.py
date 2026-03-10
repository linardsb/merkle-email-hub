"""Runtime SKILL.md content override for A/B testing.

Used by ``skill_ab.py`` to swap SKILL.md content without touching disk.
Agent prompt modules check ``get_override()`` before using file-loaded content.
"""

from __future__ import annotations

_overrides: dict[str, str] = {}


def set_override(agent: str, content: str) -> None:
    """Set SKILL.md content override for an agent."""
    _overrides[agent] = content


def clear_override(agent: str) -> None:
    """Remove SKILL.md content override for an agent."""
    _overrides.pop(agent, None)


def clear_all_overrides() -> None:
    """Remove all overrides (cleanup after A/B test)."""
    _overrides.clear()


def get_override(agent: str) -> str | None:
    """Get current SKILL.md override for an agent, or ``None`` if not set."""
    return _overrides.get(agent)
