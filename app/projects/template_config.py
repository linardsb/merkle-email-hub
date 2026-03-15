"""Template configuration models for per-project template scoping."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SectionOverride(BaseModel):
    """Override a default section block with a client component."""

    model_config = ConfigDict(frozen=True)

    section_block_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="ID of the section block to replace (e.g. 'footer_standard')",
    )
    component_version_id: int = Field(
        ...,
        ge=1,
        description="ComponentVersion ID providing the replacement",
    )


class CustomSection(BaseModel):
    """A component promoted to a section block for composition."""

    model_config = ConfigDict(frozen=True)

    component_version_id: int = Field(
        ...,
        ge=1,
        description="ComponentVersion ID to adapt as a section",
    )
    block_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Block ID for the section in the composition pipeline",
    )


class ProjectTemplateConfig(BaseModel):
    """Per-project template registry configuration."""

    model_config = ConfigDict(frozen=True)

    section_overrides: tuple[SectionOverride, ...] = ()
    custom_sections: tuple[CustomSection, ...] = ()
    disabled_templates: tuple[str, ...] = ()
    preferred_templates: tuple[str, ...] = ()

    @field_validator("disabled_templates", "preferred_templates", mode="before")
    @classmethod
    def validate_template_names(cls, v: object) -> object:
        if isinstance(v, (list, tuple)):
            for name in v:
                if not isinstance(name, str) or not name.strip():
                    msg = f"Template name must be a non-empty string, got: {name!r}"
                    raise ValueError(msg)
        return v


def load_template_config(raw: dict[str, Any] | None) -> ProjectTemplateConfig | None:
    """Parse template config from JSON column value. Returns None if raw is None or empty."""
    if not raw:
        return None
    return ProjectTemplateConfig.model_validate(raw)
