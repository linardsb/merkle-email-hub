"""Schemas for LLM judge inputs and outputs."""

from pydantic import BaseModel


class JudgeCriteria(BaseModel):
    """A single evaluation criterion."""

    name: str
    description: str


class JudgeInput(BaseModel):
    """Input to an LLM judge — one trace to evaluate."""

    trace_id: str
    agent: str
    input_data: dict[str, object]
    output_data: dict[str, object] | None
    expected_challenges: list[str]


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
