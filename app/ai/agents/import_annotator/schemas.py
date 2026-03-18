"""Import annotator structured output schemas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnnotationDecision:
    """A single section annotation decision."""

    section_id: str  # UUID assigned by the agent
    component_name: str  # Inferred: Header, Hero, Content, CTA, Footer, Columns, Divider, Spacer
    element_selector: str  # CSS-like path to the element
    layout_type: str  # "single" or "columns"
    confidence: float  # 0.0-1.0 for this specific annotation
    reasoning: str  # Why this boundary was chosen


@dataclass(frozen=True)
class ImportAnnotationResult:
    """Complete annotation result from the AI agent."""

    annotations: tuple[AnnotationDecision, ...] = ()
    warnings: tuple[str, ...] = ()  # Ambiguous sections, nested layouts, etc.
    overall_confidence: float = 0.0
    reasoning: str = ""
