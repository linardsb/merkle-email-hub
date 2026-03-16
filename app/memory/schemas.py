"""Pydantic schemas for agent memory."""

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class MemoryCreate(BaseModel):
    """Request to store a new memory entry."""

    agent_type: str = Field(..., max_length=50)
    memory_type: str = Field(..., pattern=r"^(procedural|episodic|semantic)$")
    content: str = Field(..., min_length=1, max_length=4000)
    project_id: int | None = None
    metadata: dict[str, Any] | None = None
    is_evergreen: bool = False


class MemoryResponse(BaseModel):
    """Memory entry response."""

    id: int
    agent_type: str
    memory_type: str
    content: str
    project_id: int | None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata_json", "metadata"),
    )
    decay_weight: float
    source: str
    is_evergreen: bool
    created_at: datetime
    updated_at: datetime
    similarity: float | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class MemorySearch(BaseModel):
    """Search request for memory retrieval."""

    query: str = Field(..., min_length=1, max_length=1000)
    agent_type: str | None = None
    memory_type: str | None = None
    project_id: int | None = None
    limit: int = Field(default=10, ge=1, le=50)


class MemoryPromote(BaseModel):
    """Request to promote a DCG note into Hub memory."""

    key: str = Field(..., max_length=128)
    value: str = Field(..., max_length=1024)
    agent_type: str = Field(default="dcg", max_length=50)
    project_id: int | None = None


class CompactionStats(BaseModel):
    """Result of a compaction run."""

    merged_count: int
    intent_merged_count: int = 0
    remaining_count: int
    duration_ms: int
