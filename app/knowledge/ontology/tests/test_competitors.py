"""Tests for competitive intelligence registry."""

import pytest

from app.knowledge.ontology.competitors import (
    Competitor,
    CompetitorCapability,
    CompetitorRegistry,
    HubCapability,
    load_competitors,
)


def _make_registry() -> CompetitorRegistry:
    """Build a minimal test registry."""
    capabilities = (
        CompetitorCapability(id="amp_email", name="AMP for Email", category="interactive"),
        CompetitorCapability(id="dark_mode_preview", name="Dark Mode Preview", category="testing"),
        CompetitorCapability(id="ai_code_generation", name="AI Code Generation", category="ai"),
        CompetitorCapability(id="visual_builder", name="Visual Builder", category="builder"),
    )
    competitors = (
        Competitor(
            id="stripo",
            name="Stripo",
            category="visual_builder",
            capabilities=("amp_email", "dark_mode_preview", "visual_builder"),
        ),
        Competitor(
            id="parcel",
            name="Parcel",
            category="code_editor",
            capabilities=("dark_mode_preview",),
        ),
    )
    hub_capabilities = (
        HubCapability(
            id="amp_email", name="AMP for Email", category="interactive", agent="innovation"
        ),
        HubCapability(
            id="ai_code_generation", name="AI Code Generation", category="ai", agent="scaffolder"
        ),
        HubCapability(
            id="outlook_fixes",
            name="Outlook Fixer",
            category="compatibility",
            agent="outlook_fixer",
        ),
    )
    return CompetitorRegistry(
        competitors=competitors,
        capabilities=capabilities,
        hub_capabilities=hub_capabilities,
    )


class TestCompetitorRegistry:
    def test_get_competitor(self) -> None:
        reg = _make_registry()
        assert reg.get_competitor("stripo") is not None
        assert reg.get_competitor("stripo").name == "Stripo"  # type: ignore[union-attr]
        assert reg.get_competitor("nonexistent") is None

    def test_get_capability(self) -> None:
        reg = _make_registry()
        assert reg.get_capability("amp_email") is not None
        assert reg.get_capability("nonexistent") is None

    def test_competitors_supporting(self) -> None:
        reg = _make_registry()
        # Both Stripo and Parcel support dark mode preview
        supporters = reg.competitors_supporting("dark_mode_preview")
        assert len(supporters) == 2
        assert {s.id for s in supporters} == {"stripo", "parcel"}

        # Only Stripo supports AMP
        amp_supporters = reg.competitors_supporting("amp_email")
        assert len(amp_supporters) == 1
        assert amp_supporters[0].id == "stripo"

        # Nobody supports nonexistent
        assert reg.competitors_supporting("nonexistent") == []

    def test_capabilities_of(self) -> None:
        reg = _make_registry()
        stripo_caps = reg.capabilities_of("stripo")
        assert len(stripo_caps) == 3
        assert {c.id for c in stripo_caps} == {"amp_email", "dark_mode_preview", "visual_builder"}

        parcel_caps = reg.capabilities_of("parcel")
        assert len(parcel_caps) == 1

        assert reg.capabilities_of("nonexistent") == []

    def test_hub_unique_capabilities(self) -> None:
        reg = _make_registry()
        unique = reg.hub_unique_capabilities()
        # ai_code_generation and outlook_fixes are not in any competitor
        assert len(unique) == 2
        unique_ids = {h.id for h in unique}
        assert "ai_code_generation" in unique_ids
        assert "outlook_fixes" in unique_ids

    def test_competitor_unique_capabilities(self) -> None:
        reg = _make_registry()
        # Stripo has visual_builder and dark_mode_preview which Hub doesn't have
        stripo_unique = reg.competitor_unique_capabilities("stripo")
        assert len(stripo_unique) == 2
        unique_ids = {c.id for c in stripo_unique}
        assert "visual_builder" in unique_ids
        assert "dark_mode_preview" in unique_ids

        # Parcel has dark_mode_preview — Hub doesn't have it in hub_capabilities either
        parcel_unique = reg.competitor_unique_capabilities("parcel")
        assert len(parcel_unique) == 1
        assert parcel_unique[0].id == "dark_mode_preview"

    def test_hub_vs_competitor(self) -> None:
        reg = _make_registry()
        hub_only, shared, comp_only = reg.hub_vs_competitor("stripo")

        assert "amp_email" in shared  # Both have it
        assert "ai_code_generation" in hub_only  # Hub only
        assert "outlook_fixes" in hub_only  # Hub only
        assert "visual_builder" in comp_only  # Stripo only (not in Hub capabilities)
        assert "dark_mode_preview" in comp_only  # Stripo has, Hub doesn't

    def test_hub_vs_nonexistent_competitor(self) -> None:
        reg = _make_registry()
        hub_only, shared, comp_only = reg.hub_vs_competitor("nonexistent")
        assert len(hub_only) == 3  # All Hub capabilities
        assert shared == []
        assert comp_only == []


class TestLoadCompetitors:
    def test_load_from_yaml(self) -> None:
        """Verify YAML files parse correctly."""
        registry = load_competitors()
        assert len(registry.competitors) >= 5
        assert len(registry.capabilities) >= 10
        assert len(registry.hub_capabilities) >= 10

        # Spot check known competitors
        stripo = registry.get_competitor("stripo")
        assert stripo is not None
        assert stripo.name == "Stripo"
        assert len(stripo.capabilities) > 0

        parcel = registry.get_competitor("parcel")
        assert parcel is not None
        assert parcel.name == "Parcel"

    def test_frozen_dataclasses(self) -> None:
        """Verify data is immutable."""
        registry = load_competitors()
        comp = registry.competitors[0]
        with pytest.raises(AttributeError):
            comp.name = "Modified"  # type: ignore[misc]

    def test_capability_references_valid(self) -> None:
        """All capability IDs referenced by competitors exist in the capability list."""
        registry = load_competitors()
        cap_ids = {c.id for c in registry.capabilities}
        for comp in registry.competitors:
            for cap_id in comp.capabilities:
                assert cap_id in cap_ids, f"{comp.id} references unknown capability: {cap_id}"
