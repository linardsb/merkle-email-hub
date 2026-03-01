"""Model tier routing for AI provider calls.

Maps task complexity tiers to specific model identifiers.
Agents specify their required tier; the router resolves to a concrete model.
"""

from typing import Literal

from app.core.config import get_settings
from app.core.logging import get_logger

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
