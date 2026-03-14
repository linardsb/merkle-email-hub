"""Golden template library for deterministic email assembly."""

from app.ai.templates.models import (
    GoldenTemplate,
    LayoutType,
    SlotType,
    TemplateMetadata,
    TemplateSlot,
)
from app.ai.templates.registry import TemplateRegistry, get_template_registry

__all__ = [
    "GoldenTemplate",
    "LayoutType",
    "SlotType",
    "TemplateMetadata",
    "TemplateRegistry",
    "TemplateSlot",
    "get_template_registry",
]
