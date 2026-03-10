"""Email development ontology type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SupportLevel(Enum):
    """CSS property support level in an email client."""

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"
    UNKNOWN = "unknown"


class ClientEngine(Enum):
    """Rendering engine used by email clients."""

    WEBKIT = "webkit"
    BLINK = "blink"
    WORD = "word"
    GECKO = "gecko"
    PRESTO = "presto"
    CUSTOM = "custom"


class CSSCategory(Enum):
    """CSS property categories for grouping."""

    LAYOUT = "layout"
    BOX_MODEL = "box_model"
    TYPOGRAPHY = "typography"
    COLOR_BACKGROUND = "color_background"
    BORDER_SHADOW = "border_shadow"
    TRANSFORM_ANIMATION = "transform_animation"
    SELECTOR = "selector"
    MEDIA_QUERY = "media_query"
    DARK_MODE = "dark_mode"
    TABLE = "table"
    LIST = "list"
    FLEXBOX = "flexbox"
    GRID = "grid"
    OTHER = "other"


@dataclass(frozen=True)
class EmailClient:
    """An email client with version and rendering engine metadata."""

    id: str
    name: str
    family: str
    platform: str
    engine: ClientEngine
    market_share: float = 0.0
    notes: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class CSSProperty:
    """A CSS property or feature tracked in the ontology."""

    id: str
    property_name: str
    value: str | None = None
    category: CSSCategory = CSSCategory.OTHER
    description: str = ""
    mdn_url: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class SupportEntry:
    """A single property x client support record."""

    property_id: str
    client_id: str
    level: SupportLevel
    notes: str = ""
    fallback_ids: tuple[str, ...] = ()
    workaround: str = ""


@dataclass(frozen=True)
class Fallback:
    """A fallback/workaround relationship between properties."""

    id: str
    source_property_id: str
    target_property_id: str
    client_ids: tuple[str, ...] = ()
    technique: str = ""
    code_example: str = ""
