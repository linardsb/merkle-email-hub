"""Data models for the golden template library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SlotType = Literal[
    "headline",
    "subheadline",
    "body",
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
class GoldenTemplate:
    """A pre-validated email template skeleton."""

    metadata: TemplateMetadata
    html: str
    slots: tuple[TemplateSlot, ...]
    maizzle_source: str = ""
