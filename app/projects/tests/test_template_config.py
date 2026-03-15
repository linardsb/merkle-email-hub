# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
# mypy: disable-error-code="method-assign"
"""Tests for project-scoped template configuration models and registry methods."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.ai.templates.models import GoldenTemplate, TemplateMetadata
from app.ai.templates.registry import TemplateRegistry
from app.projects.template_config import (
    CustomSection,
    ProjectTemplateConfig,
    SectionOverride,
    load_template_config,
)

# ── load_template_config ──


class TestLoadTemplateConfig:
    def test_none_returns_none(self) -> None:
        assert load_template_config(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert load_template_config({}) is None

    def test_valid_round_trip(self) -> None:
        raw: dict[str, Any] = {
            "section_overrides": [
                {"section_block_id": "footer_standard", "component_version_id": 42}
            ],
            "custom_sections": [{"component_version_id": 7, "block_id": "hero_custom"}],
            "disabled_templates": ["promotional_grid"],
            "preferred_templates": ["newsletter_1col"],
        }
        config = load_template_config(raw)
        assert config is not None
        dumped = config.model_dump()
        reloaded = load_template_config(dumped)
        assert reloaded is not None
        assert reloaded.disabled_templates == ("promotional_grid",)
        assert reloaded.preferred_templates == ("newsletter_1col",)
        assert len(reloaded.section_overrides) == 1
        assert reloaded.section_overrides[0].section_block_id == "footer_standard"


# ── Model defaults ──


class TestProjectTemplateConfigDefaults:
    def test_defaults_are_empty_tuples(self) -> None:
        config = ProjectTemplateConfig()
        assert config.section_overrides == ()
        assert config.custom_sections == ()
        assert config.disabled_templates == ()
        assert config.preferred_templates == ()


# ── Validation ──


class TestSectionOverrideValidation:
    def test_uppercase_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SectionOverride(section_block_id="Footer", component_version_id=1)

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SectionOverride(section_block_id="", component_version_id=1)

    def test_valid_id_accepted(self) -> None:
        override = SectionOverride(section_block_id="footer_standard", component_version_id=1)
        assert override.section_block_id == "footer_standard"


class TestCustomSectionValidation:
    def test_invalid_pattern_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CustomSection(component_version_id=1, block_id="Hero-Custom")

    def test_valid_block_id_accepted(self) -> None:
        section = CustomSection(component_version_id=1, block_id="hero_custom")
        assert section.block_id == "hero_custom"


class TestDisabledTemplatesValidation:
    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProjectTemplateConfig(disabled_templates=("",))

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProjectTemplateConfig(disabled_templates=("  ",))


# ── Registry methods ──


def _make_template(name: str, description: str = "A template") -> GoldenTemplate:
    return GoldenTemplate(
        metadata=TemplateMetadata(
            name=name,
            display_name=name.replace("_", " ").title(),
            layout_type="single_column",  # type: ignore[arg-type]
            column_count=1,
            has_hero_image=False,
            has_navigation=False,
            has_social_links=False,
            sections=(),
            ideal_for=(),
            description=description,
        ),
        html="<html></html>",
        slots=(),
        maizzle_source="",
        default_tokens=None,
    )


def _make_registry(names: list[str]) -> TemplateRegistry:
    """Create a registry pre-loaded with named templates."""
    registry = TemplateRegistry()
    for name in names:
        registry._templates[name] = _make_template(name)
    registry._loaded = True
    return registry


class TestGetForProject:
    def test_none_config_returns_full_list(self) -> None:
        registry = _make_registry(["a", "b", "c"])
        result = registry.get_for_project(None)
        assert len(result) == 3

    def test_disabled_excluded(self) -> None:
        registry = _make_registry(["a", "b", "c"])
        config = ProjectTemplateConfig(disabled_templates=("b",))
        result = registry.get_for_project(config)
        names = [t.metadata.name for t in result]
        assert "b" not in names
        assert len(names) == 2

    def test_preferred_first(self) -> None:
        registry = _make_registry(["a", "b", "c"])
        config = ProjectTemplateConfig(preferred_templates=("c",))
        result = registry.get_for_project(config)
        assert result[0].metadata.name == "c"

    def test_disabled_and_preferred_together(self) -> None:
        """Disabled takes precedence — a template in both is excluded."""
        registry = _make_registry(["a", "b", "c"])
        config = ProjectTemplateConfig(disabled_templates=("b",), preferred_templates=("b", "c"))
        result = registry.get_for_project(config)
        names = [t.metadata.name for t in result]
        assert "b" not in names
        assert names[0] == "c"  # c is preferred and first


class TestListForSelectionScoped:
    def test_recommended_marker(self) -> None:
        registry = _make_registry(["a", "b"])
        config = ProjectTemplateConfig(preferred_templates=("a",))
        result = registry.list_for_selection_scoped(config)
        a_meta = next(m for m in result if m.name == "a")
        b_meta = next(m for m in result if m.name == "b")
        assert a_meta.description.startswith("[RECOMMENDED]")
        assert not b_meta.description.startswith("[RECOMMENDED]")
