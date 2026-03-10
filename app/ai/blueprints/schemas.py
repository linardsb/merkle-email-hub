"""Pydantic schemas for blueprint API requests and responses."""

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
        default_factory=list,
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
    handoff_history: list[HandoffSummary] = Field(default_factory=list)
    audience_summary: str | None = None
