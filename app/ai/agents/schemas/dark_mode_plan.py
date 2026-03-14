"""Structured output schema for the Dark Mode agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ColorMapping:
    """A single light-to-dark color mapping."""

    light_color: str
    dark_color: str
    selector: str
    property: str


@dataclass(frozen=True)
class DarkModePlan:
    """Structured plan for dark mode transformation."""

    meta_tag_strategy: Literal["color-scheme", "supported-color-schemes", "both"]
    color_mappings: tuple[ColorMapping, ...]
    outlook_override_strategy: Literal["mso-conditional", "data-attribute", "none"]
    preserve_brand_colors: tuple[str, ...]
    custom_media_query_css: str | None = None
    reasoning: str = ""
