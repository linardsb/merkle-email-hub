"""Pydantic schemas for multimodal content blocks in API transport.

These schemas handle base64 encoding/decoding of binary data for JSON transport.
Used by any API endpoint that accepts or returns multimodal content.
"""

from __future__ import annotations

import base64
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.ai.multimodal import (
    AudioBlock,
    ContentBlock,
    ImageBlock,
    StructuredOutputBlock,
    TextBlock,
    ToolResultBlock,
)


class TextBlockSchema(BaseModel):
    """API schema for text content blocks."""

    type: Literal["text"] = "text"
    text: str


class ImageBlockSchema(BaseModel):
    """API schema for image content blocks.

    Binary data is base64-encoded for JSON transport.
    """

    type: Literal["image"] = "image"
    data: str = ""  # base64-encoded
    media_type: str
    source: str = "base64"
    url: str = ""
    width: int | None = None
    height: int | None = None

    @field_validator("data")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        if v:
            try:
                base64.b64decode(v, validate=True)
            except Exception as e:
                msg = f"Invalid base64 data: {e}"
                raise ValueError(msg) from e
        return v


class AudioBlockSchema(BaseModel):
    """API schema for audio content blocks."""

    type: Literal["audio"] = "audio"
    data: str = ""  # base64-encoded
    media_type: str
    duration_seconds: float | None = None

    @field_validator("data")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        if v:
            try:
                base64.b64decode(v, validate=True)
            except Exception as e:
                msg = f"Invalid base64 data: {e}"
                raise ValueError(msg) from e
        return v


class StructuredOutputBlockSchema(BaseModel):
    """API schema for structured output blocks."""

    type: Literal["structured_output"] = "structured_output"
    schema_def: dict[str, Any] = Field(default_factory=dict, alias="schema")
    name: str = "response"
    strict: bool = True

    model_config = {"populate_by_name": True}


class ToolResultBlockSchema(BaseModel):
    """API schema for tool result blocks."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: list[ContentBlockSchema] = []


# Discriminated union for API transport
ContentBlockSchema = (
    TextBlockSchema
    | ImageBlockSchema
    | AudioBlockSchema
    | StructuredOutputBlockSchema
    | ToolResultBlockSchema
)

# Update ToolResultBlockSchema's forward reference
ToolResultBlockSchema.model_rebuild()


class MultimodalMessageSchema(BaseModel):
    """API schema for a multimodal message."""

    role: str
    content: str | list[ContentBlockSchema]


# --- Conversion helpers ---


def schema_to_block(schema: ContentBlockSchema) -> ContentBlock:
    """Convert an API schema to an internal ContentBlock."""
    if isinstance(schema, TextBlockSchema):
        return TextBlock(text=schema.text)
    if isinstance(schema, ImageBlockSchema):
        data = base64.b64decode(schema.data) if schema.data else b""
        return ImageBlock(
            data=data,
            media_type=schema.media_type,
            source=schema.source,
            url=schema.url,
            width=schema.width,
            height=schema.height,
        )
    if isinstance(schema, AudioBlockSchema):
        data = base64.b64decode(schema.data) if schema.data else b""
        return AudioBlock(
            data=data,
            media_type=schema.media_type,
            duration_seconds=schema.duration_seconds,
        )
    if isinstance(schema, StructuredOutputBlockSchema):
        return StructuredOutputBlock(
            schema=schema.schema_def,
            name=schema.name,
            strict=schema.strict,
        )
    if isinstance(schema, ToolResultBlockSchema):
        return ToolResultBlock(
            tool_use_id=schema.tool_use_id,
            content=[schema_to_block(c) for c in schema.content],
        )
    msg = f"Unknown schema type: {type(schema).__name__}"
    raise ValueError(msg)


def block_to_schema(block: ContentBlock) -> ContentBlockSchema:
    """Convert an internal ContentBlock to an API schema."""
    if isinstance(block, TextBlock):
        return TextBlockSchema(text=block.text)
    if isinstance(block, ImageBlock):
        data_b64 = base64.b64encode(block.data).decode("ascii") if block.data else ""
        return ImageBlockSchema(
            data=data_b64,
            media_type=block.media_type,
            source=block.source,
            url=block.url,
            width=block.width,
            height=block.height,
        )
    if isinstance(block, AudioBlock):
        data_b64 = base64.b64encode(block.data).decode("ascii") if block.data else ""
        return AudioBlockSchema(
            data=data_b64,
            media_type=block.media_type,
            duration_seconds=block.duration_seconds,
        )
    if isinstance(block, StructuredOutputBlock):
        return StructuredOutputBlockSchema(
            schema=block.schema,
            name=block.name,
            strict=block.strict,
        )
    if isinstance(block, ToolResultBlock):
        return ToolResultBlockSchema(
            tool_use_id=block.tool_use_id,
            content=[block_to_schema(b) for b in block.content],
        )
    msg = f"Unknown block type: {type(block).__name__}"
    raise ValueError(msg)
