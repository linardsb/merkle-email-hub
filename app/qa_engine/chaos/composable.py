"""Profile composition for stacking multiple chaos degradations."""

from __future__ import annotations

from collections.abc import Callable

from app.qa_engine.chaos.profiles import ChaosProfile


def compose_profiles(*profiles: ChaosProfile) -> ChaosProfile:
    """Stack multiple chaos profiles into a single composite profile.

    Transformations are applied in order: first profile's transforms,
    then second profile's, etc.
    """
    if not profiles:
        msg = "At least one profile is required"
        raise ValueError(msg)

    names = " + ".join(p.name for p in profiles)
    descriptions = "; ".join(p.description for p in profiles)
    all_transforms: tuple[Callable[[str], str], ...] = ()
    for p in profiles:
        all_transforms = (*all_transforms, *p.transformations)

    return ChaosProfile(
        name=f"composed({names})",
        description=f"Composed: {descriptions}",
        transformations=all_transforms,
    )
