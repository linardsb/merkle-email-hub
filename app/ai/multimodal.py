"""Multimodal content block protocol for LLM messages.

Typed union of content blocks that agents produce and adapters serialize
per-provider. Replaces raw string content with structured blocks supporting
text, images, audio, structured output, and tool results.
"""

from __future__ import annotations

import json as _json_mod
import re
import struct
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level json.dumps for performance (avoids per-call import)
_json_dumps = _json_mod.dumps

__all__ = [
    "AudioBlock",
    "ContentBlock",
    "ContentBlockValidationError",
    "ImageBlock",
    "StructuredOutputBlock",
    "TextBlock",
    "ToolResultBlock",
    "estimate_block_tokens",
    "estimate_blocks_tokens",
    "normalize_content",
    "validate_content_block",
    "validate_content_blocks",
]

# --- Constants ---

_SUPPORTED_IMAGE_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
    }
)

_SUPPORTED_AUDIO_TYPES = frozenset(
    {
        "audio/wav",
        "audio/mp3",
        "audio/webm",
        "audio/ogg",
        "audio/mpeg",  # alias for mp3
    }
)

_MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20MB — Anthropic limit
_MAX_AUDIO_BYTES = 100 * 1024 * 1024  # 100MB — generous cap for voice briefs
_MAX_AUDIO_DURATION_S = 300  # 5 minutes

# Magic bytes for MIME type validation
_MAGIC_BYTES: dict[str, list[bytes]] = {
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # RIFF....WEBP — check first 4 bytes
    "audio/wav": [b"RIFF"],  # RIFF....WAVE
    "audio/mp3": [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"ID3"],
    "audio/mpeg": [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"ID3"],
    "audio/ogg": [b"OggS"],
    "audio/webm": [b"\x1a\x45\xdf\xa3"],  # EBML header
}

# Blocked schema fields for StructuredOutputBlock
_BLOCKED_SCHEMA_KEYS = frozenset({"$ref", "$dynamicRef"})


# --- Content Block Types ---


@dataclass(frozen=True)
class TextBlock:
    """Plain text content block."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            msg = f"TextBlock.text must be str, got {type(self.text).__name__}"
            raise TypeError(msg)


@dataclass(frozen=True)
class ImageBlock:
    """Image content block with MIME type validation.

    Attributes:
        data: Raw image bytes (when source="base64") or empty (when source="url").
        media_type: MIME type (image/png, image/jpeg, image/gif, image/webp).
        source: "base64" for inline data, "url" for provider-resolved URLs.
        url: Image URL when source="url".
        width: Optional width in pixels (for token estimation).
        height: Optional height in pixels (for token estimation).
    """

    data: bytes
    media_type: str
    source: str = "base64"
    url: str = ""
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class AudioBlock:
    """Audio content block for voice briefs.

    Attributes:
        data: Raw audio bytes.
        media_type: MIME type (audio/wav, audio/mp3, audio/webm, audio/ogg).
        duration_seconds: Optional duration for validation.
    """

    data: bytes
    media_type: str
    duration_seconds: float | None = None


_VALID_SCHEMA_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


@dataclass(frozen=True)
class StructuredOutputBlock:
    """JSON Schema for structured output.

    Adapters use provider-specific structured output modes
    (OpenAI response_format, Anthropic tool use).
    """

    schema: dict[str, Any] = field(default_factory=dict)
    name: str = "response"  # Schema name for tool_use pattern
    strict: bool = True

    def __post_init__(self) -> None:
        if not _VALID_SCHEMA_NAME.match(self.name):
            msg = f"StructuredOutputBlock.name must match [a-zA-Z0-9_-]{{1,64}}, got {self.name!r}"
            raise ValueError(msg)


@dataclass(frozen=True)
class ToolResultBlock:
    """Tool result passthrough for MCP integration.

    Attributes:
        tool_use_id: The ID of the tool use this is a result for.
        content: Nested content blocks (text, images, etc.).
    """

    tool_use_id: str
    content: list[ContentBlock] = field(default_factory=list)


# Union type — all possible content blocks
ContentBlock = TextBlock | ImageBlock | AudioBlock | StructuredOutputBlock | ToolResultBlock


# --- Validation ---


def _check_magic_bytes(data: bytes, media_type: str) -> bool:
    """Verify data starts with expected magic bytes for the declared MIME type."""
    patterns = _MAGIC_BYTES.get(media_type, [])
    if not patterns:
        return True  # No pattern registered — skip check
    return any(data[: len(p)] == p for p in patterns)


_MAX_SCHEMA_DEPTH = 50  # Guard against pathologically nested schemas


def _check_schema_refs(
    schema: dict[str, Any],
    path: str = "",
    *,
    _depth: int = 0,
) -> list[str]:
    """Recursively check for blocked $ref / $dynamicRef in JSON Schema.

    Only internal JSON pointer refs (starting with ``#``) are allowed.
    All other refs (http, https, file, relative paths) are blocked.
    """
    if _depth > _MAX_SCHEMA_DEPTH:
        return [f"Schema nesting exceeds maximum depth of {_MAX_SCHEMA_DEPTH} at {path or 'root'}"]

    errors: list[str] = []
    for key, value in schema.items():
        if key in _BLOCKED_SCHEMA_KEYS:
            if isinstance(value, str) and not value.startswith("#"):
                errors.append(f"External {key} not allowed at {path or 'root'}: {value}")
        if isinstance(value, dict):
            errors.extend(_check_schema_refs(value, f"{path}/{key}", _depth=_depth + 1))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    errors.extend(_check_schema_refs(item, f"{path}/{key}[{i}]", _depth=_depth + 1))
    return errors


class ContentBlockValidationError(ValueError):
    """Raised when a content block fails validation."""


def validate_content_block(block: ContentBlock) -> ContentBlock:
    """Validate a content block for size limits, MIME types, and schema safety.

    Args:
        block: The content block to validate.

    Returns:
        The validated block (unchanged).

    Raises:
        ContentBlockValidationError: If validation fails.
    """
    if isinstance(block, TextBlock):
        return block

    if isinstance(block, ImageBlock):
        if block.source == "base64":
            if len(block.data) > _MAX_IMAGE_BYTES:
                msg = (
                    f"Image size {len(block.data)} bytes exceeds "
                    f"limit of {_MAX_IMAGE_BYTES} bytes ({_MAX_IMAGE_BYTES // (1024 * 1024)}MB)"
                )
                raise ContentBlockValidationError(msg)
            if block.media_type not in _SUPPORTED_IMAGE_TYPES:
                msg = (
                    f"Unsupported image type: {block.media_type}. "
                    f"Supported: {sorted(_SUPPORTED_IMAGE_TYPES)}"
                )
                raise ContentBlockValidationError(msg)
            if block.data and not _check_magic_bytes(block.data, block.media_type):
                msg = f"Image data magic bytes do not match declared type {block.media_type}"
                raise ContentBlockValidationError(msg)
        elif block.source == "url":
            if not block.url:
                msg = "ImageBlock with source='url' must have a non-empty url"
                raise ContentBlockValidationError(msg)
        else:
            msg = f"Invalid image source: {block.source}. Must be 'base64' or 'url'"
            raise ContentBlockValidationError(msg)
        return block

    if isinstance(block, AudioBlock):
        if len(block.data) > _MAX_AUDIO_BYTES:
            msg = (
                f"Audio size {len(block.data)} bytes exceeds "
                f"limit of {_MAX_AUDIO_BYTES} bytes ({_MAX_AUDIO_BYTES // (1024 * 1024)}MB)"
            )
            raise ContentBlockValidationError(msg)
        if block.media_type not in _SUPPORTED_AUDIO_TYPES:
            msg = (
                f"Unsupported audio type: {block.media_type}. "
                f"Supported: {sorted(_SUPPORTED_AUDIO_TYPES)}"
            )
            raise ContentBlockValidationError(msg)
        if block.data and not _check_magic_bytes(block.data, block.media_type):
            msg = f"Audio data magic bytes do not match declared type {block.media_type}"
            raise ContentBlockValidationError(msg)
        if block.duration_seconds is not None and block.duration_seconds > _MAX_AUDIO_DURATION_S:
            msg = (
                f"Audio duration {block.duration_seconds}s exceeds "
                f"limit of {_MAX_AUDIO_DURATION_S}s"
            )
            raise ContentBlockValidationError(msg)
        return block

    if isinstance(block, StructuredOutputBlock):
        errors = _check_schema_refs(block.schema)
        if errors:
            msg = f"Blocked schema references: {'; '.join(errors)}"
            raise ContentBlockValidationError(msg)
        return block

    if isinstance(block, ToolResultBlock):
        for nested in block.content:
            validate_content_block(nested)
        return block

    # Should be unreachable with proper typing, but guard anyway
    msg = f"Unknown content block type: {type(block).__name__}"
    raise ContentBlockValidationError(msg)


def validate_content_blocks(blocks: list[ContentBlock]) -> list[ContentBlock]:
    """Validate a list of content blocks."""
    for block in blocks:
        validate_content_block(block)
    return blocks


# --- Token Estimation ---

# Anthropic image token formula: (width * height) / 750
_IMAGE_TOKENS_PER_PIXEL = 1 / 750
_IMAGE_DEFAULT_TOKENS = 1_000  # Fallback when dimensions unknown
_AUDIO_TOKENS_PER_SECOND = 25  # Approximate: ~1500 tokens/minute


def estimate_block_tokens(block: ContentBlock) -> int:
    """Estimate token count for a single content block.

    For text: uses char / 4.0 approximation (same as TokenBudgetManager).
    For images: width*height/750 (Anthropic formula) or default 1000.
    For audio: ~25 tokens/second.
    For structured output / tool result: estimates based on schema size / nested content.
    """
    if isinstance(block, TextBlock):
        return max(1, int(len(block.text) / 4.0))

    if isinstance(block, ImageBlock):
        if block.width and block.height:
            return max(1, int(block.width * block.height * _IMAGE_TOKENS_PER_PIXEL))
        # Try to read dimensions from PNG header
        if block.source == "base64" and block.data and block.media_type == "image/png":
            tokens = _estimate_png_tokens(block.data)
            if tokens:
                return tokens
        return _IMAGE_DEFAULT_TOKENS

    if isinstance(block, AudioBlock):
        if block.duration_seconds is not None:
            return max(1, int(block.duration_seconds * _AUDIO_TOKENS_PER_SECOND))
        # Rough estimate from file size: ~16KB/s for MP3 at 128kbps
        return max(1, int(len(block.data) / 16_000 * _AUDIO_TOKENS_PER_SECOND))

    if isinstance(block, StructuredOutputBlock):
        return max(1, int(len(_json_dumps(block.schema)) / 4.0))

    if isinstance(block, ToolResultBlock):
        return sum(estimate_block_tokens(b) for b in block.content) or 1

    return 1


def estimate_blocks_tokens(blocks: list[ContentBlock]) -> int:
    """Estimate total tokens for a list of content blocks."""
    return sum(estimate_block_tokens(b) for b in blocks)


def _estimate_png_tokens(data: bytes) -> int | None:
    """Try to extract PNG dimensions from IHDR chunk for token estimation."""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    try:
        width = struct.unpack(">I", data[16:20])[0]
        height = struct.unpack(">I", data[20:24])[0]
        if width > 0 and height > 0:
            return max(1, int(width * height * _IMAGE_TOKENS_PER_PIXEL))
    except struct.error:
        pass
    return None


# --- Normalization (backward compatibility) ---


def normalize_content(content: str | list[ContentBlock]) -> list[ContentBlock]:
    """Normalize message content to a list of ContentBlock.

    If content is a plain string, wraps it in a single TextBlock.
    If content is already a list of ContentBlock, returns as-is.

    This provides backward compatibility — existing code passing ``str`` content
    continues to work without changes.
    """
    if isinstance(content, str):
        return [TextBlock(text=content)]
    return content
