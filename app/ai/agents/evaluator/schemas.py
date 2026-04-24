"""Request/response schemas for the Evaluator agent."""

from typing import Literal

from pydantic import BaseModel, Field


class EvalIssue(BaseModel):
    """A single evaluation finding."""

    severity: Literal["critical", "major", "minor"]
    category: str = Field(
        description="Issue category (e.g., 'layout', 'accessibility', 'dark_mode')"
    )
    description: str = Field(description="Human-readable description of the defect")
    location: str | None = Field(default=None, description="CSS selector or section hint")


class EvalVerdict(BaseModel):
    """Structured verdict from the evaluator agent."""

    verdict: Literal["accept", "revise", "reject"]
    score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    issues: list[EvalIssue] = Field(default_factory=list[EvalIssue])
    feedback: str = ""
    suggested_corrections: list[str] = Field(default_factory=list)


class EvaluatorRequest(BaseModel):
    """Request body for the Evaluator agent."""

    original_brief: str = Field(min_length=1, description="Original campaign brief")
    agent_name: str = Field(description="Name of the upstream agent that produced the output")
    agent_output: str = Field(min_length=1, description="HTML or content output to evaluate")
    quality_criteria: list[str] = Field(default_factory=list)
    iteration: int = Field(default=0, ge=0)
    previous_feedback: str | None = None


class EvaluatorResponse(BaseModel):
    """Response from the Evaluator agent."""

    verdict: EvalVerdict
    model: str
    confidence: float | None = None
    skills_loaded: list[str] = Field(default_factory=list)
