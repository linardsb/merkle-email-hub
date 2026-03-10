"""Route advisor — audience-aware node relevance for blueprint execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.blueprints.audience_context import AudienceProfile

from app.core.logging import get_logger
from app.knowledge.ontology.types import ClientEngine

logger = get_logger(__name__)


def is_node_relevant(
    node_name: str,
    audience_profile: AudienceProfile | None,
) -> bool:
    """Determine whether a blueprint node is relevant for the target audience.

    Returns True (relevant) when:
    - No audience profile is set (backward compatible — skip nothing)
    - The node has no audience-dependent relevance rule
    - The audience matches the node's relevance criteria

    Returns False (skip) when the audience data proves the node unnecessary.
    """
    if audience_profile is None:
        return True

    rule = _RELEVANCE_RULES.get(node_name)
    if rule is None:
        return True  # No rule → always relevant

    return rule(audience_profile)


def _has_word_engine_client(profile: AudienceProfile) -> bool:
    """True if any target client uses the Word rendering engine (Outlook desktop)."""
    return any(c.engine == ClientEngine.WORD for c in profile.clients)


def _needs_dark_mode(profile: AudienceProfile) -> bool:
    """True if any persona requires dark mode support."""
    return profile.dark_mode_required


# Maps node names to relevance check functions.
# Nodes NOT listed here are always relevant.
_RELEVANCE_RULES: dict[str, Callable[[AudienceProfile], bool]] = {
    "outlook_fixer": _has_word_engine_client,
    "dark_mode": _needs_dark_mode,
}
