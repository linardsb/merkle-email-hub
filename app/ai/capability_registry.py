"""Model capability registry for capability-aware routing.

Each model declares capabilities, constraints, and metadata.
The registry matches task requirements to model capabilities
rather than relying solely on tier names.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import StrEnum, unique
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@unique
class ModelCapability(StrEnum):
    """Capabilities a model may support."""

    VISION = "vision"
    TOOL_USE = "tool_use"
    STRUCTURED_OUTPUT = "structured_output"
    EXTENDED_THINKING = "extended_thinking"
    JSON_MODE = "json_mode"
    STREAMING = "streaming"
    FUNCTION_CALLING = "function_calling"


@dataclass(frozen=True)
class ModelConstraints:
    """Resource constraints for a model."""

    context_window: int = 128_000
    max_output_tokens: int = 4_096
    cost_per_input_token: float = 0.0  # USD per token
    cost_per_output_token: float = 0.0  # USD per token


@dataclass(frozen=True)
class ModelSpec:
    """Complete specification for a registered model.

    Attributes:
        model_id: Unique model identifier (e.g. "claude-sonnet-4-20250514").
        provider: Provider name (e.g. "anthropic", "openai", "ollama").
        tier: Default task tier this model maps to.
        capabilities: Set of supported capabilities.
        constraints: Resource constraints (context window, costs, etc.).
        is_local: Whether the model runs locally (vs cloud API).
        deprecation_date: Optional date when this model will be deprecated.
        metadata: Arbitrary additional metadata.
    """

    model_id: str
    provider: str
    tier: str = "standard"  # default TaskTier
    capabilities: frozenset[ModelCapability] = field(default_factory=frozenset)
    constraints: ModelConstraints = field(default_factory=ModelConstraints)
    is_local: bool = False
    deprecation_date: datetime.date | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_deprecated(self) -> bool:
        """Check if model is past its deprecation date."""
        if self.deprecation_date is None:
            return False
        return datetime.datetime.now(tz=datetime.UTC).date() >= self.deprecation_date

    def satisfies(
        self,
        requirements: set[ModelCapability] | None = None,
        min_context: int = 0,
        min_output_tokens: int = 0,
    ) -> bool:
        """Check whether this model meets the given requirements."""
        if requirements and not requirements <= self.capabilities:
            return False
        if min_context > 0 and self.constraints.context_window < min_context:
            return False
        return not (
            min_output_tokens > 0 and self.constraints.max_output_tokens < min_output_tokens
        )


class CapabilityRegistry:
    """Registry of model specifications.

    Maps model IDs to their specifications.
    Supports querying by capabilities, constraints, and tier.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelSpec] = {}

    def register(self, spec: ModelSpec) -> None:
        """Register a model specification."""
        self._models[spec.model_id] = spec
        logger.debug(
            "capability_registry.model_registered",
            model_id=spec.model_id,
            provider=spec.provider,
            capabilities=[c.value for c in spec.capabilities],
        )

    def get(self, model_id: str) -> ModelSpec | None:
        """Get a model spec by ID."""
        return self._models.get(model_id)

    def find_models(
        self,
        requirements: set[ModelCapability] | None = None,
        min_context: int = 0,
        min_output_tokens: int = 0,
        tier: str | None = None,
        provider: str | None = None,
        exclude_deprecated: bool = True,
    ) -> list[ModelSpec]:
        """Find models matching the given requirements.

        Results are sorted by cost (cheapest first), then by context window
        (largest first) as a tiebreaker.

        Args:
            requirements: Required capabilities the model must support.
            min_context: Minimum context window size in tokens.
            min_output_tokens: Minimum max output tokens.
            tier: Optional tier filter.
            provider: Optional provider filter.
            exclude_deprecated: Whether to exclude deprecated models.

        Returns:
            List of matching ModelSpec sorted by cost ascending.
        """
        results: list[ModelSpec] = []
        for spec in self._models.values():
            if exclude_deprecated and spec.is_deprecated:
                continue
            if tier is not None and spec.tier != tier:
                continue
            if provider is not None and spec.provider != provider:
                continue
            if not spec.satisfies(requirements, min_context, min_output_tokens):
                continue
            results.append(spec)

        # Sort: cheapest input cost first, then largest context as tiebreaker
        results.sort(
            key=lambda s: (
                s.constraints.cost_per_input_token,
                -s.constraints.context_window,
            )
        )
        return results

    def list_all(self) -> list[ModelSpec]:
        """Return all registered models."""
        return list(self._models.values())

    @property
    def size(self) -> int:
        """Number of registered models."""
        return len(self._models)

    def clear(self) -> None:
        """Remove all registered models (for testing)."""
        self._models.clear()


# ── Module-level singleton ──

_registry: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    """Get or create the global capability registry singleton."""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry


def load_model_specs_from_config(specs: list[dict[str, Any]]) -> None:
    """Load model specs from configuration (AI__MODEL_SPECS).

    Each dict in the list should have:
        - model_id (str, required)
        - provider (str, required)
        - tier (str, optional, default "standard")
        - capabilities (list[str], optional)
        - context_window (int, optional)
        - max_output_tokens (int, optional)
        - cost_per_input_token (float, optional)
        - cost_per_output_token (float, optional)
        - is_local (bool, optional)
        - deprecation_date (str ISO format, optional)
    """
    registry = get_capability_registry()
    for raw in specs:
        model_id = raw.get("model_id", "")
        if not model_id:
            logger.warning("capability_registry.skip_empty_model_id")
            continue

        caps = frozenset(
            ModelCapability(c)
            for c in raw.get("capabilities", [])
            if c in ModelCapability._value2member_map_
        )

        dep_date: datetime.date | None = None
        if raw.get("deprecation_date"):
            try:
                dep_date = datetime.date.fromisoformat(raw["deprecation_date"])
            except ValueError:
                logger.warning(
                    "capability_registry.invalid_deprecation_date",
                    model_id=model_id,
                    value=raw["deprecation_date"],
                )

        constraints = ModelConstraints(
            context_window=raw.get("context_window", 128_000),
            max_output_tokens=raw.get("max_output_tokens", 4_096),
            cost_per_input_token=raw.get("cost_per_input_token", 0.0),
            cost_per_output_token=raw.get("cost_per_output_token", 0.0),
        )

        spec = ModelSpec(
            model_id=model_id,
            provider=raw.get("provider", "unknown"),
            tier=raw.get("tier", "standard"),
            capabilities=caps,
            constraints=constraints,
            is_local=raw.get("is_local", False),
            deprecation_date=dep_date,
        )
        registry.register(spec)

    logger.info(
        "capability_registry.loaded",
        model_count=registry.size,
    )
