"""Model tier routing for AI provider calls.

Maps task complexity tiers to specific model identifiers.
Agents specify their required tier; the router resolves to a concrete model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.ai.routing_history import RoutingHistoryRepository

logger = get_logger(__name__)

TaskTier = Literal["complex", "standard", "lightweight"]


def resolve_model(tier: TaskTier | None = None) -> str:
    """Resolve a task complexity tier to a concrete model identifier.

    Falls back to the default model (settings.ai.model) when:
    - No tier is specified
    - The tier's model is not configured (empty string)

    Args:
        tier: Task complexity tier, or None for default model.

    Returns:
        Model identifier string to pass to the provider.
    """
    settings = get_settings()
    default_model = settings.ai.model

    if tier is None:
        return default_model

    tier_model_map: dict[TaskTier, str] = {
        "complex": settings.ai.model_complex,
        "standard": settings.ai.model_standard,
        "lightweight": settings.ai.model_lightweight,
    }

    model = tier_model_map.get(tier, "") or default_model

    if model != default_model:
        logger.debug(
            "ai.routing.tier_resolved",
            tier=tier,
            model=model,
        )

    return model


async def resolve_model_adaptive(
    tier: TaskTier,
    agent_name: str,
    project_id: int | None,
    routing_repo: RoutingHistoryRepository | None,
) -> tuple[str, TaskTier]:
    """Resolve model with adaptive tier adjustment.

    Returns (model_id, effective_tier) so callers can record which tier was used.
    """
    effective_tier = tier
    if routing_repo is not None:
        from app.ai.routing_history import resolve_adaptive_tier

        effective_tier = await resolve_adaptive_tier(tier, agent_name, project_id, routing_repo)

    model = resolve_model(effective_tier)
    return model, effective_tier
