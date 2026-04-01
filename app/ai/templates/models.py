"""Data models for the golden template library."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

SlotType = Literal[
    "headline",
    "subheadline",
    "body",
    "content",
    "text",
    "attr",
    "cta",
    "image",
    "preheader",
    "footer",
    "nav",
    "social",
    "divider",
]

LayoutType = Literal[
    "newsletter",
    "promotional",
    "transactional",
    "event",
    "retention",
    "announcement",
    "minimal",
]


@dataclass(frozen=True)
class TemplateSlot:
    """A content slot within a golden template."""

    slot_id: str
    slot_type: SlotType
    selector: str
    required: bool = True
    max_chars: int | None = None
    placeholder: str = ""


@dataclass(frozen=True)
class TemplateMetadata:
    """Metadata for template selection by the LLM."""

    name: str
    display_name: str
    layout_type: LayoutType
    column_count: int
    has_hero_image: bool
    has_navigation: bool
    has_social_links: bool
    sections: tuple[str, ...]
    ideal_for: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class DefaultTokens:
    """A template's built-in default values, keyed by semantic role."""

    colors: dict[str, str] = field(default_factory=dict[str, str])
    fonts: dict[str, str] = field(default_factory=dict[str, str])
    font_sizes: dict[str, str] = field(default_factory=dict[str, str])
    spacing: dict[str, str] = field(default_factory=dict[str, str])
    font_weights: dict[str, str] = field(default_factory=dict[str, str])
    line_heights: dict[str, str] = field(default_factory=dict[str, str])
    letter_spacings: dict[str, str] = field(default_factory=dict[str, str])
    responsive: dict[str, str] = field(default_factory=dict[str, str])
    responsive_breakpoints: tuple[str, ...] = ()


@dataclass(frozen=True)
class GoldenTemplate:
    """A pre-validated email template skeleton."""

    metadata: TemplateMetadata
    html: str
    slots: tuple[TemplateSlot, ...]
    maizzle_source: str = ""
    default_tokens: DefaultTokens | None = None
    source: Literal["builtin", "uploaded"] = "builtin"
    project_id: int | None = None  # project scope (None = global)
    # Precompilation (26.3)
    optimized_html: str | None = None
    optimized_at: datetime | None = None
    optimized_for_clients: tuple[str, ...] = ()
    optimization_metadata: dict[str, object] = field(default_factory=dict)
    # Wrapper reconstruction (31.4)
    wrapper_metadata: dict[str, str | None] | None = None
