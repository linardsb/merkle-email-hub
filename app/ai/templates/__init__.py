"""Golden template library for deterministic email assembly."""

from app.ai.templates.composer import (
    CompositionError,
    SectionBlock,
    TemplateComposer,
    get_composer,
)
from app.ai.templates.models import (
    GoldenTemplate,
    LayoutType,
    SlotType,
    TemplateMetadata,
    TemplateSlot,
)
from app.ai.templates.registry import TemplateRegistry, get_template_registry

__all__ = [
    "CompositionError",
    "GoldenTemplate",
    "LayoutType",
    "SectionBlock",
    "SlotType",
    "TemplateComposer",
    "TemplateMetadata",
    "TemplateRegistry",
    "TemplateSlot",
    "get_composer",
    "get_template_registry",
]
