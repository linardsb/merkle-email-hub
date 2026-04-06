"""Hook profile levels for pipeline execution hooks."""

from __future__ import annotations

from typing import Literal

HookProfile = Literal["minimal", "standard", "strict"]

PROFILE_LEVELS: dict[HookProfile, int] = {"minimal": 0, "standard": 1, "strict": 2}


def profile_includes(active: HookProfile, required: HookProfile) -> bool:
    """Check if active profile includes hooks registered at required level.

    Higher profiles include all lower-level hooks:
    strict >= standard >= minimal.
    """
    return PROFILE_LEVELS[active] >= PROFILE_LEVELS[required]
