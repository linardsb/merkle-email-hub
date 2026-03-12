"""Braze Content Blocks API schemas."""

from pydantic import BaseModel


class ContentBlockCreate(BaseModel):
    name: str
    content: str
    tags: list[str] = []


class ContentBlockUpdate(BaseModel):
    content_block_id: str
    content: str
    tags: list[str] | None = None


class ContentBlockSummary(BaseModel):
    content_block_id: str
    name: str
    tags: list[str]
    created_at: str
    updated_at: str


class ContentBlockResponse(BaseModel):
    content_block_id: str
    name: str
    content: str
    tags: list[str]
    created_at: str
    updated_at: str
    message: str = "success"


class ContentBlockListResponse(BaseModel):
    content_blocks: list[ContentBlockSummary]
    count: int
    message: str = "success"
