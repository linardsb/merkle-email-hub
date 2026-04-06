"""Email component tree schema — constrained output format for AI agents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- SlotValue discriminated union ---


class TextSlot(BaseModel):
    """Text content slot."""

    type: Literal["text"] = "text"
    text: str = Field(..., min_length=1)
    tag: str = Field(default="td", pattern=r"^(td|span|a)$")


class ImageSlot(BaseModel):
    """Image slot with dimensions."""

    type: Literal["image"] = "image"
    src: str = Field(..., min_length=1)
    alt: str
    width: int = Field(..., gt=0, le=2000)
    height: int = Field(..., gt=0, le=2000)


class ButtonSlot(BaseModel):
    """CTA button slot."""

    type: Literal["button"] = "button"
    text: str = Field(..., min_length=1)
    href: str = Field(..., min_length=1)
    bg_color: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    text_color: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")


class HtmlSlot(BaseModel):
    """Raw HTML slot (for custom/complex content)."""

    type: Literal["html"] = "html"
    html: str = Field(..., min_length=1)


SlotValue = Annotated[
    TextSlot | ImageSlot | ButtonSlot | HtmlSlot,
    Field(discriminator="type"),
]

# --- CSS validation ---

_CSS_PROP_RE = re.compile(
    r"^(-?[a-z][a-z-]*[a-z]|--[a-z][a-z0-9-]*)$",  # standard props + CSS custom properties
)


# --- Tree models ---


class TreeMetadata(BaseModel):
    """Email-level metadata."""

    subject: str = Field(..., min_length=1, max_length=500)
    preheader: str = Field(default="", max_length=250)
    design_tokens: dict[str, dict[str, str]] = Field(default_factory=dict)
    template_id: str | None = None


class TreeSection(BaseModel):
    """A section referencing a component from the manifest."""

    component_slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^([a-z][a-z0-9-]*|__custom__)$",
    )
    slot_fills: dict[str, SlotValue] = Field(default_factory=dict)
    style_overrides: dict[str, str] = Field(default_factory=dict)
    children: list[TreeSection] | None = None
    custom_html: str | None = None

    @model_validator(mode="after")
    def _validate_custom_html(self) -> TreeSection:
        if self.custom_html is not None and self.component_slug != "__custom__":
            msg = "custom_html is only allowed when component_slug is '__custom__'"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_style_keys(self) -> TreeSection:
        for key in self.style_overrides:
            if not _CSS_PROP_RE.match(key):
                msg = f"Invalid CSS property name: '{key}'"
                raise ValueError(msg)
        return self


class EmailTree(BaseModel):
    """Root model: an email as a tree of component references."""

    metadata: TreeMetadata
    sections: list[TreeSection] = Field(..., min_length=1)

    model_config = ConfigDict(
        json_schema_extra={
            "title": "EmailTree",
            "description": (
                "An email represented as a tree of component references"
                " with slot fills and style overrides."
            ),
        },
    )


# --- Manifest cross-validation ---


def validate_tree_against_manifest(
    tree: EmailTree,
    manifest_slugs: set[str],
    slot_definitions: dict[str, list[str]],
) -> list[str]:
    """Validate component slugs and slot names against manifest.

    Returns list of validation error messages (empty = valid).
    """
    errors: list[str] = []
    for i, section in enumerate(tree.sections):
        _validate_section(section, f"sections[{i}]", manifest_slugs, slot_definitions, errors)
    return errors


def _validate_section(
    section: TreeSection,
    path: str,
    manifest_slugs: set[str],
    slot_definitions: dict[str, list[str]],
    errors: list[str],
) -> None:
    slug = section.component_slug
    if slug != "__custom__" and slug not in manifest_slugs:
        errors.append(f"{path}: unknown component_slug '{slug}'")
    elif slug in slot_definitions:
        valid_slots = set(slot_definitions[slug])
        for slot_key in section.slot_fills:
            if slot_key not in valid_slots:
                errors.append(f"{path}: slot '{slot_key}' not defined for component '{slug}'")
    if section.children:
        for j, child in enumerate(section.children):
            _validate_section(
                child,
                f"{path}.children[{j}]",
                manifest_slugs,
                slot_definitions,
                errors,
            )


# --- JSON Schema export ---


def export_json_schema() -> dict[str, object]:
    """Export EmailTree JSON Schema for external tooling."""
    return EmailTree.model_json_schema()


def write_json_schema(path: Path | None = None) -> Path:
    """Write JSON Schema to file. Returns the path written."""
    if path is None:
        path = Path(__file__).parent / "schemas" / "email-tree.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = export_json_schema()
    path.write_text(json.dumps(schema, indent=2) + "\n")
    return path
