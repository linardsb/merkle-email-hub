"""Schemas for LLM judge inputs and outputs."""

from pydantic import BaseModel, Field


class JudgeCriteria(BaseModel):
    """A single evaluation criterion."""

    name: str
    description: str


class DesignTokenSummary(BaseModel):
    """Extracted design tokens from Figma for judge comparison."""

    colors: dict[str, str] = Field(default_factory=dict)
    fonts: dict[str, str] = Field(default_factory=dict)
    font_sizes: dict[str, str] = Field(default_factory=dict)
    spacing: dict[str, str] = Field(default_factory=dict)


class SectionDesignMapping(BaseModel):
    """Maps a built HTML section back to its Figma frame + source component."""

    section_index: int
    component_slug: str
    figma_frame_name: str | None = None
    slot_fills: dict[str, str] = Field(default_factory=dict)
    style_overrides: dict[str, str] = Field(default_factory=dict)


class DesignContext(BaseModel):
    """Figma/Penpot design source metadata for fidelity scoring (eval-only)."""

    figma_url: str | None = None
    node_id: str | None = None
    file_id: str | None = None
    design_tokens: DesignTokenSummary | None = None
    section_mapping: list[SectionDesignMapping] = Field(default_factory=list[SectionDesignMapping])


class JudgeInput(BaseModel):
    """Input to an LLM judge — one trace to evaluate."""

    trace_id: str
    agent: str
    input_data: dict[str, object]
    output_data: dict[str, object] | None
    expected_challenges: list[str]
    design_context: DesignContext | None = None


class CriterionResult(BaseModel):
    """Result for a single criterion."""

    criterion: str
    passed: bool
    reasoning: str


class JudgeVerdict(BaseModel):
    """Structured output from an LLM judge."""

    trace_id: str
    agent: str
    overall_pass: bool
    criteria_results: list[CriterionResult]
    error: str | None = None
