"""Pydantic schemas for knowledge base feature."""

import json
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class DocumentUpload(BaseModel):
    """Schema for document upload metadata (sent alongside file)."""

    domain: str = Field(..., min_length=1, max_length=50, description="Knowledge domain")
    language: str = Field(
        default="en", pattern="^[a-z]{2}$", description="Document language (ISO 639-1)"
    )
    metadata_json: str | None = Field(None, description="Optional JSON metadata string")
    title: str | None = Field(None, max_length=200, description="Human-readable document title")
    description: str | None = Field(None, description="Optional document description")

    @field_validator("metadata_json")
    @classmethod
    def validate_metadata_json(cls, v: str | None) -> str | None:
        """Ensure metadata_json is valid JSON if provided."""
        if v is None:
            return v
        if len(v) > 10_000:
            raise ValueError("metadata_json must not exceed 10,000 characters")
        try:
            json.loads(v)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"metadata_json must be valid JSON: {e}") from e
        return v


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata (PATCH semantics)."""

    title: str | None = None
    description: str | None = None
    domain: str | None = Field(None, min_length=1, max_length=50)
    language: str | None = Field(None, pattern="^[a-z]{2}$")

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> Self:
        """Reject empty PATCH bodies that would cause unnecessary DB round-trips."""
        if not any(v is not None for v in self.model_dump(exclude_unset=True).values()):
            raise ValueError("At least one field must be provided for update")
        return self


class TagCreate(BaseModel):
    """Schema for creating a new tag."""

    name: str = Field(..., min_length=1, max_length=100, description="Tag name")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Strip whitespace and lowercase tag names for consistency."""
        return v.strip().lower()


class TagResponse(BaseModel):
    """Schema for tag responses."""

    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    """Schema for listing all tags."""

    tags: list[TagResponse]
    total: int


class DocumentTagRequest(BaseModel):
    """Schema for adding tags to a document."""

    tag_ids: list[int] = Field(..., min_length=1, max_length=20, description="Tag IDs to assign")


class DocumentResponse(BaseModel):
    """Schema for document responses."""

    id: int
    filename: str
    title: str | None
    description: str | None
    domain: str
    source_type: str
    language: str
    file_size_bytes: int | None
    status: str
    error_message: str | None
    chunk_count: int
    metadata_json: str | None
    ocr_applied: bool
    tags: list[TagResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_file(self) -> bool:
        """Whether the original file is stored on disk."""
        return self.file_size_bytes is not None and self.file_size_bytes > 0


class DocumentChunkResponse(BaseModel):
    """Schema for a single document chunk."""

    chunk_index: int
    content: str
    section_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentContentResponse(BaseModel):
    """Schema wrapping document metadata with its text chunks."""

    document_id: int
    filename: str
    title: str | None
    total_chunks: int
    chunks: list[DocumentChunkResponse]


class DomainListResponse(BaseModel):
    """Schema for listing unique knowledge domains."""

    domains: list[str]
    total: int


class SearchRequest(BaseModel):
    """Schema for knowledge base search."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    domain: str | None = Field(None, description="Filter by domain")
    language: str | None = Field(None, description="Filter by language")
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return")


class SearchResult(BaseModel):
    """Single search result with relevance score."""

    chunk_content: str
    document_id: int
    document_filename: str
    domain: str
    language: str
    chunk_index: int
    score: float
    metadata_json: str | None


class SearchResponse(BaseModel):
    """Search response with results and metadata."""

    results: list[SearchResult]
    query: str
    total_candidates: int
    reranked: bool
    intent: str | None = None  # Query intent classification (16.1)


# ---------------------------------------------------------------------------
# Graph knowledge schemas
# ---------------------------------------------------------------------------


class GraphSearchRequest(BaseModel):
    """Request body for graph knowledge search."""

    query: str = Field(..., min_length=1, max_length=2000)
    dataset_name: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    mode: Literal["chunks", "completion"] = "chunks"
    system_prompt: str = ""


class GraphEntityResponse(BaseModel):
    """An entity from the knowledge graph."""

    id: str
    name: str
    entity_type: str
    description: str = ""
    properties: dict[str, object] = Field(default_factory=dict)


class GraphRelationshipResponse(BaseModel):
    """A relationship edge between entities."""

    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, object] = Field(default_factory=dict)


class GraphSearchResultResponse(BaseModel):
    """A single graph search result."""

    content: str
    entities: list[GraphEntityResponse] = Field(default_factory=list)
    relationships: list[GraphRelationshipResponse] = Field(default_factory=list)
    score: float = 0.0


class GraphSearchResponse(BaseModel):
    """Response for graph knowledge search."""

    results: list[GraphSearchResultResponse]
    query: str
    mode: str
