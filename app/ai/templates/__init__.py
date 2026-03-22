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
from app.ai.templates.precompiler import (
    CSS_PREOPTIMIZED_MARKER,
    PrecompilationReport,
    TemplatePrecompiler,
)
from app.ai.templates.registry import TemplateRegistry, get_template_registry

__all__ = [
    "CSS_PREOPTIMIZED_MARKER",
    "CompositionError",
    "GoldenTemplate",
    "LayoutType",
    "PrecompilationReport",
    "SectionBlock",
    "SlotType",
    "TemplateComposer",
    "TemplateMetadata",
    "TemplatePrecompiler",
    "TemplateRegistry",
    "TemplateSlot",
    "get_composer",
    "get_template_registry",
]
