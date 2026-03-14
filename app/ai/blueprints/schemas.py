"""Pydantic schemas for blueprint API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class BlueprintRunRequest(BaseModel):
    """Request to execute a named blueprint."""

    blueprint_name: str = Field(description="Registered blueprint name (e.g. 'campaign')")
    brief: str = Field(description="Campaign brief or instructions for agentic nodes")
    initial_html: str = Field(default="", description="Pre-existing HTML to process")
    options: dict[str, object] = Field(
        default_factory=dict, description="Blueprint-specific options"
    )
    persona_ids: list[int] = Field(
        default_factory=lambda: list[int](),
        description="Target audience persona IDs — agents will adapt output for these clients",
    )


class BlueprintProgress(BaseModel):
    """Progress entry for a single node execution within a blueprint run."""

    node_name: str
    node_type: str
    status: str
    iteration: int
    summary: str
    duration_ms: float


class HandoffSummary(BaseModel):
    """Summary of the last agent handoff in a blueprint run."""

    agent_name: str
    decisions: list[str]
    warnings: list[str]
    component_refs: list[str]
    confidence: float | None = None


class RoutingDecisionResponse(BaseModel):
    """A single routing decision from the route advisor."""

    node_name: str
    action: str  # "skip" or "prioritise"
    reason: str


class InlineJudgeCriterionResponse(BaseModel):
    """Result for a single judge criterion in an inline verdict."""

    criterion: str
    passed: bool
    reasoning: str


class InlineJudgeVerdictResponse(BaseModel):
    """Inline judge verdict from a recovery retry."""

    trace_id: str
    agent: str
    overall_pass: bool
    criteria_results: list[InlineJudgeCriterionResponse]


class BlueprintRunResponse(BaseModel):
    """Response from a completed blueprint run."""

    run_id: str
    blueprint_name: str
    status: str
    html: str
    progress: list[BlueprintProgress]
    qa_passed: bool | None = None
    model_usage: dict[str, int] = Field(default_factory=dict)
    final_handoff: HandoffSummary | None = None
    handoff_history: list[HandoffSummary] = Field(default_factory=lambda: list[HandoffSummary]())
    audience_summary: str | None = None
    skipped_nodes: list[str] = Field(default_factory=lambda: list[str]())
    routing_decisions: list[RoutingDecisionResponse] = Field(
        default_factory=lambda: list[RoutingDecisionResponse]()
    )
    judge_verdict: InlineJudgeVerdictResponse | None = None


class FailurePatternResponse(BaseModel):
    """A failure pattern extracted from blueprint runs."""

    id: int
    agent_name: str
    qa_check: str
    client_ids: list[str]
    description: str
    workaround: str
    confidence: float | None = None
    run_id: str
    blueprint_name: str
    first_seen: datetime
    last_seen: datetime
    frequency: int = 1


class FailurePatternListResponse(BaseModel):
    """Paginated list of failure patterns."""

    items: list[FailurePatternResponse]
    total: int
    page: int
    page_size: int


class FailurePatternStats(BaseModel):
    """Aggregated failure pattern statistics."""

    total_patterns: int
    unique_agents: int
    unique_checks: int
    top_agent: str | None = None
    top_check: str | None = None
