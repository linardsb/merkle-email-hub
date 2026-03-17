"""Tests for model capability registry (22.1)."""

from __future__ import annotations

import datetime

import pytest

from app.ai.capability_registry import (
    CapabilityRegistry,
    ModelCapability,
    ModelConstraints,
    ModelSpec,
    load_model_specs_from_config,
)

# ── Fixtures ──


@pytest.fixture
def registry() -> CapabilityRegistry:
    """Fresh registry for each test."""
    return CapabilityRegistry()


@pytest.fixture
def claude_sonnet() -> ModelSpec:
    return ModelSpec(
        model_id="claude-sonnet-4-20250514",
        provider="anthropic",
        tier="standard",
        capabilities=frozenset(
            {
                ModelCapability.VISION,
                ModelCapability.TOOL_USE,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.STREAMING,
            }
        ),
        constraints=ModelConstraints(
            context_window=200_000,
            max_output_tokens=8_192,
            cost_per_input_token=0.000003,
            cost_per_output_token=0.000015,
        ),
    )


@pytest.fixture
def gpt4o_mini() -> ModelSpec:
    return ModelSpec(
        model_id="gpt-4o-mini",
        provider="openai",
        tier="lightweight",
        capabilities=frozenset(
            {
                ModelCapability.VISION,
                ModelCapability.TOOL_USE,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.JSON_MODE,
                ModelCapability.STREAMING,
            }
        ),
        constraints=ModelConstraints(
            context_window=128_000,
            max_output_tokens=4_096,
            cost_per_input_token=0.00000015,
            cost_per_output_token=0.0000006,
        ),
    )


@pytest.fixture
def deprecated_model() -> ModelSpec:
    return ModelSpec(
        model_id="gpt-4-legacy",
        provider="openai",
        tier="complex",
        capabilities=frozenset({ModelCapability.TOOL_USE}),
        deprecation_date=datetime.date(2024, 1, 1),
    )


# ── ModelSpec tests ──


def test_model_spec_frozen(claude_sonnet: ModelSpec) -> None:
    with pytest.raises(AttributeError):
        claude_sonnet.model_id = "changed"  # type: ignore[misc]


def test_satisfies_all_requirements(claude_sonnet: ModelSpec) -> None:
    assert claude_sonnet.satisfies(
        requirements={ModelCapability.VISION, ModelCapability.TOOL_USE},
        min_context=100_000,
    )


def test_satisfies_no_requirements(claude_sonnet: ModelSpec) -> None:
    assert claude_sonnet.satisfies()


def test_fails_missing_capability(gpt4o_mini: ModelSpec) -> None:
    assert not gpt4o_mini.satisfies(
        requirements={ModelCapability.EXTENDED_THINKING},
    )


def test_fails_insufficient_context(gpt4o_mini: ModelSpec) -> None:
    assert not gpt4o_mini.satisfies(min_context=200_000)


def test_fails_insufficient_output_tokens(gpt4o_mini: ModelSpec) -> None:
    assert not gpt4o_mini.satisfies(min_output_tokens=8_192)


def test_is_deprecated(deprecated_model: ModelSpec) -> None:
    assert deprecated_model.is_deprecated


def test_not_deprecated(claude_sonnet: ModelSpec) -> None:
    assert not claude_sonnet.is_deprecated


# ── CapabilityRegistry tests ──


def test_register_and_get(registry: CapabilityRegistry, claude_sonnet: ModelSpec) -> None:
    registry.register(claude_sonnet)
    assert registry.get("claude-sonnet-4-20250514") is claude_sonnet
    assert registry.size == 1


def test_get_unknown_returns_none(registry: CapabilityRegistry) -> None:
    assert registry.get("nonexistent") is None


def test_find_by_capabilities(
    registry: CapabilityRegistry,
    claude_sonnet: ModelSpec,
    gpt4o_mini: ModelSpec,
) -> None:
    registry.register(claude_sonnet)
    registry.register(gpt4o_mini)

    # Both have vision + tool_use
    results = registry.find_models(
        requirements={ModelCapability.VISION, ModelCapability.TOOL_USE},
    )
    assert len(results) == 2
    # Cheapest first (gpt4o_mini)
    assert results[0].model_id == "gpt-4o-mini"


def test_find_by_json_mode(
    registry: CapabilityRegistry,
    claude_sonnet: ModelSpec,
    gpt4o_mini: ModelSpec,
) -> None:
    registry.register(claude_sonnet)
    registry.register(gpt4o_mini)

    results = registry.find_models(
        requirements={ModelCapability.JSON_MODE},
    )
    assert len(results) == 1
    assert results[0].model_id == "gpt-4o-mini"


def test_find_by_min_context(
    registry: CapabilityRegistry,
    claude_sonnet: ModelSpec,
    gpt4o_mini: ModelSpec,
) -> None:
    registry.register(claude_sonnet)
    registry.register(gpt4o_mini)

    results = registry.find_models(min_context=150_000)
    assert len(results) == 1
    assert results[0].model_id == "claude-sonnet-4-20250514"


def test_find_by_tier(
    registry: CapabilityRegistry,
    claude_sonnet: ModelSpec,
    gpt4o_mini: ModelSpec,
) -> None:
    registry.register(claude_sonnet)
    registry.register(gpt4o_mini)

    results = registry.find_models(tier="lightweight")
    assert len(results) == 1
    assert results[0].model_id == "gpt-4o-mini"


def test_find_by_provider(
    registry: CapabilityRegistry,
    claude_sonnet: ModelSpec,
    gpt4o_mini: ModelSpec,
) -> None:
    registry.register(claude_sonnet)
    registry.register(gpt4o_mini)

    results = registry.find_models(provider="anthropic")
    assert len(results) == 1
    assert results[0].model_id == "claude-sonnet-4-20250514"


def test_find_excludes_deprecated(
    registry: CapabilityRegistry,
    deprecated_model: ModelSpec,
) -> None:
    registry.register(deprecated_model)
    assert registry.find_models() == []
    assert registry.find_models(exclude_deprecated=False) == [deprecated_model]


def test_find_no_matches(registry: CapabilityRegistry, gpt4o_mini: ModelSpec) -> None:
    registry.register(gpt4o_mini)
    results = registry.find_models(
        requirements={ModelCapability.EXTENDED_THINKING},
    )
    assert results == []


def test_list_all(
    registry: CapabilityRegistry,
    claude_sonnet: ModelSpec,
    gpt4o_mini: ModelSpec,
) -> None:
    registry.register(claude_sonnet)
    registry.register(gpt4o_mini)
    assert len(registry.list_all()) == 2


def test_clear(registry: CapabilityRegistry, claude_sonnet: ModelSpec) -> None:
    registry.register(claude_sonnet)
    registry.clear()
    assert registry.size == 0


# ── load_model_specs_from_config tests ──


def test_load_from_config() -> None:
    """Config JSON correctly populates the registry."""
    reg = CapabilityRegistry()
    import app.ai.capability_registry as mod

    old = mod._registry
    mod._registry = reg
    try:
        load_model_specs_from_config(
            [
                {
                    "model_id": "test-model",
                    "provider": "test",
                    "tier": "complex",
                    "capabilities": ["vision", "tool_use"],
                    "context_window": 256_000,
                    "max_output_tokens": 16_384,
                    "cost_per_input_token": 0.00001,
                    "cost_per_output_token": 0.00003,
                    "deprecation_date": "2026-12-31",
                },
            ]
        )
        spec = reg.get("test-model")
        assert spec is not None
        assert spec.provider == "test"
        assert spec.tier == "complex"
        assert ModelCapability.VISION in spec.capabilities
        assert ModelCapability.TOOL_USE in spec.capabilities
        assert spec.constraints.context_window == 256_000
        assert spec.constraints.max_output_tokens == 16_384
        assert spec.deprecation_date == datetime.date(2026, 12, 31)
    finally:
        mod._registry = old


def test_load_skips_empty_model_id() -> None:
    """Entries without model_id are skipped."""
    reg = CapabilityRegistry()
    import app.ai.capability_registry as mod

    old = mod._registry
    mod._registry = reg
    try:
        load_model_specs_from_config([{"provider": "test"}])
        assert reg.size == 0
    finally:
        mod._registry = old


def test_load_invalid_deprecation_date() -> None:
    """Invalid deprecation_date is gracefully ignored."""
    reg = CapabilityRegistry()
    import app.ai.capability_registry as mod

    old = mod._registry
    mod._registry = reg
    try:
        load_model_specs_from_config(
            [
                {"model_id": "test", "provider": "test", "deprecation_date": "not-a-date"},
            ]
        )
        spec = reg.get("test")
        assert spec is not None
        assert spec.deprecation_date is None
    finally:
        mod._registry = old


def test_load_unknown_capability_ignored() -> None:
    """Unknown capability strings are silently skipped."""
    reg = CapabilityRegistry()
    import app.ai.capability_registry as mod

    old = mod._registry
    mod._registry = reg
    try:
        load_model_specs_from_config(
            [
                {
                    "model_id": "test",
                    "provider": "test",
                    "capabilities": ["vision", "teleportation"],
                },
            ]
        )
        spec = reg.get("test")
        assert spec is not None
        assert spec.capabilities == frozenset({ModelCapability.VISION})
    finally:
        mod._registry = old


# ── resolve_model_by_capabilities tests ──


def test_resolve_by_capabilities_empty_registry() -> None:
    """Empty registry returns None."""
    import app.ai.capability_registry as mod
    from app.ai.routing import resolve_model_by_capabilities

    old = mod._registry
    mod._registry = CapabilityRegistry()
    try:
        result = resolve_model_by_capabilities(
            requirements={ModelCapability.VISION},
        )
        assert result is None
    finally:
        mod._registry = old


def test_resolve_by_capabilities_returns_cheapest() -> None:
    """Returns cheapest matching model."""
    import app.ai.capability_registry as mod
    from app.ai.routing import resolve_model_by_capabilities

    old = mod._registry
    reg = CapabilityRegistry()
    mod._registry = reg

    reg.register(
        ModelSpec(
            model_id="expensive",
            provider="a",
            capabilities=frozenset({ModelCapability.VISION}),
            constraints=ModelConstraints(cost_per_input_token=0.01),
        )
    )
    reg.register(
        ModelSpec(
            model_id="cheap",
            provider="b",
            capabilities=frozenset({ModelCapability.VISION}),
            constraints=ModelConstraints(cost_per_input_token=0.001),
        )
    )

    try:
        result = resolve_model_by_capabilities(
            requirements={ModelCapability.VISION},
        )
        assert result == "cheap"
    finally:
        mod._registry = old
