"""Tests for multimodal content block protocol (Phase 23.1)."""

from __future__ import annotations

import json
import struct

import pytest

from app.ai.multimodal import (
    AudioBlock,
    ContentBlock,
    ContentBlockValidationError,
    ImageBlock,
    StructuredOutputBlock,
    TextBlock,
    ToolResultBlock,
    estimate_block_tokens,
    estimate_blocks_tokens,
    normalize_content,
    validate_content_block,
    validate_content_blocks,
)

# --- Helpers ---


def _make_png_header(width: int = 100, height: int = 100) -> bytes:
    """Build minimal PNG header with IHDR dimensions."""
    header = b"\x89PNG\r\n\x1a\n"
    # IHDR chunk: 4-byte length + 'IHDR' + data (13 bytes) + CRC
    ihdr_data = struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00"
    ihdr_length = struct.pack(">I", len(ihdr_data))
    ihdr_crc = b"\x00\x00\x00\x00"  # dummy CRC
    return header + ihdr_length + b"IHDR" + ihdr_data + ihdr_crc


def _make_jpeg_header() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100


def _make_gif_header() -> bytes:
    return b"GIF89a" + b"\x00" * 100


def _make_wav_header() -> bytes:
    return b"RIFF" + b"\x00" * 100


def _make_ogg_header() -> bytes:
    return b"OggS" + b"\x00" * 100


# ── TextBlock ──


class TestTextBlock:
    def test_creation(self) -> None:
        block = TextBlock(text="hello")
        assert block.text == "hello"

    def test_non_str_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be str"):
            TextBlock(text=123)  # type: ignore[arg-type]

    def test_empty_string_ok(self) -> None:
        block = TextBlock(text="")
        assert block.text == ""


# ── ImageBlock Validation ──


class TestImageBlockValidation:
    def test_valid_png(self) -> None:
        data = _make_png_header()
        block = ImageBlock(data=data, media_type="image/png")
        result = validate_content_block(block)
        assert result is block

    def test_valid_jpeg(self) -> None:
        data = _make_jpeg_header()
        block = ImageBlock(data=data, media_type="image/jpeg")
        validate_content_block(block)

    def test_oversized_rejected(self) -> None:
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * (21 * 1024 * 1024)
        block = ImageBlock(data=data, media_type="image/png")
        with pytest.raises(ContentBlockValidationError, match="exceeds limit"):
            validate_content_block(block)

    def test_unsupported_mime_rejected(self) -> None:
        block = ImageBlock(data=b"\x00\x00", media_type="image/bmp")
        with pytest.raises(ContentBlockValidationError, match="Unsupported image type"):
            validate_content_block(block)

    def test_magic_bytes_mismatch_rejected(self) -> None:
        # Declare PNG but provide JPEG magic bytes
        data = _make_jpeg_header()
        block = ImageBlock(data=data, media_type="image/png")
        with pytest.raises(ContentBlockValidationError, match="magic bytes"):
            validate_content_block(block)

    def test_url_source_requires_url(self) -> None:
        block = ImageBlock(data=b"", media_type="image/png", source="url", url="")
        with pytest.raises(ContentBlockValidationError, match="non-empty url"):
            validate_content_block(block)

    def test_base64_source_empty_data_ok(self) -> None:
        block = ImageBlock(data=b"", media_type="image/png", source="base64")
        validate_content_block(block)

    def test_invalid_source_rejected(self) -> None:
        block = ImageBlock(data=b"", media_type="image/png", source="file")
        with pytest.raises(ContentBlockValidationError, match="Invalid image source"):
            validate_content_block(block)


# ── AudioBlock Validation ──


class TestAudioBlockValidation:
    def test_valid_wav(self) -> None:
        data = _make_wav_header()
        block = AudioBlock(data=data, media_type="audio/wav")
        validate_content_block(block)

    def test_unsupported_mime(self) -> None:
        block = AudioBlock(data=b"\x00", media_type="audio/flac")
        with pytest.raises(ContentBlockValidationError, match="Unsupported audio type"):
            validate_content_block(block)

    def test_magic_bytes_mismatch(self) -> None:
        # Declare WAV but provide OGG data
        data = _make_ogg_header()
        block = AudioBlock(data=data, media_type="audio/wav")
        with pytest.raises(ContentBlockValidationError, match="magic bytes"):
            validate_content_block(block)

    def test_duration_exceeds_limit(self) -> None:
        block = AudioBlock(data=b"", media_type="audio/mp3", duration_seconds=600)
        with pytest.raises(ContentBlockValidationError, match="exceeds limit"):
            validate_content_block(block)

    def test_duration_within_limit_ok(self) -> None:
        block = AudioBlock(data=b"", media_type="audio/mp3", duration_seconds=300)
        validate_content_block(block)

    def test_oversized_audio_rejected(self) -> None:
        data = b"\xff\xfb" + b"\x00" * (101 * 1024 * 1024)
        block = AudioBlock(data=data, media_type="audio/mp3")
        with pytest.raises(ContentBlockValidationError, match="exceeds limit"):
            validate_content_block(block)


# ── StructuredOutputBlock Validation ──


class TestStructuredOutputBlockValidation:
    def test_valid_schema(self) -> None:
        block = StructuredOutputBlock(schema={"type": "object", "properties": {}})
        validate_content_block(block)

    def test_external_ref_rejected(self) -> None:
        block = StructuredOutputBlock(schema={"$ref": "https://evil.com/schema.json"})
        with pytest.raises(ContentBlockValidationError, match="Blocked schema"):
            validate_content_block(block)

    def test_nested_external_ref_rejected(self) -> None:
        block = StructuredOutputBlock(
            schema={
                "type": "object",
                "properties": {"name": {"$ref": "https://evil.com/name.json"}},
            }
        )
        with pytest.raises(ContentBlockValidationError, match="Blocked schema"):
            validate_content_block(block)

    def test_deeply_nested_schema_rejected(self) -> None:
        """Schema exceeding max depth is rejected."""
        # Build a schema nested 60 levels deep
        schema: dict[str, object] = {"type": "string"}
        for _i in range(60):
            schema = {"type": "object", "properties": {"nested": schema}}
        block = StructuredOutputBlock(schema=schema)
        with pytest.raises(ContentBlockValidationError, match="nesting exceeds"):
            validate_content_block(block)

    def test_invalid_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="must match"):
            StructuredOutputBlock(name="bad name with spaces")

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="must match"):
            StructuredOutputBlock(name="")

    def test_valid_name_ok(self) -> None:
        block = StructuredOutputBlock(name="my_schema-v2")
        assert block.name == "my_schema-v2"

    def test_internal_ref_ok(self) -> None:
        block = StructuredOutputBlock(schema={"$ref": "#/definitions/Thing"})
        validate_content_block(block)  # Internal refs are fine

    def test_file_ref_rejected(self) -> None:
        block = StructuredOutputBlock(schema={"$ref": "file:///etc/passwd"})
        with pytest.raises(ContentBlockValidationError, match="Blocked schema"):
            validate_content_block(block)

    def test_relative_path_ref_rejected(self) -> None:
        block = StructuredOutputBlock(schema={"$ref": "../other/schema.json"})
        with pytest.raises(ContentBlockValidationError, match="Blocked schema"):
            validate_content_block(block)


# ── ToolResultBlock Validation ──


class TestToolResultBlockValidation:
    def test_valid_with_nested_blocks(self) -> None:
        block = ToolResultBlock(
            tool_use_id="test-123",
            content=[TextBlock(text="result")],
        )
        validate_content_block(block)

    def test_nested_validation_failure_propagates(self) -> None:
        block = ToolResultBlock(
            tool_use_id="test-456",
            content=[ImageBlock(data=b"", media_type="image/bmp")],
        )
        with pytest.raises(ContentBlockValidationError, match="Unsupported image type"):
            validate_content_block(block)

    def test_empty_content_ok(self) -> None:
        block = ToolResultBlock(tool_use_id="test-789")
        validate_content_block(block)


# ── normalize_content ──


class TestNormalizeContent:
    def test_string_to_text_block(self) -> None:
        result = normalize_content("hello")
        assert len(result) == 1
        assert isinstance(result[0], TextBlock)
        assert result[0].text == "hello"

    def test_list_passthrough(self) -> None:
        blocks: list[ContentBlock] = [TextBlock(text="a"), TextBlock(text="b")]
        result = normalize_content(blocks)
        assert result is blocks

    def test_empty_string(self) -> None:
        result = normalize_content("")
        assert len(result) == 1
        assert isinstance(result[0], TextBlock)
        assert result[0].text == ""


# ── estimate_block_tokens ──


class TestEstimateBlockTokens:
    def test_text_estimation(self) -> None:
        block = TextBlock(text="a" * 400)
        assert estimate_block_tokens(block) == 100

    def test_image_with_dimensions(self) -> None:
        block = ImageBlock(data=b"", media_type="image/png", width=1000, height=750)
        # 1000 * 750 / 750 = 1000
        assert estimate_block_tokens(block) == 1000

    def test_image_without_dimensions_default(self) -> None:
        block = ImageBlock(data=b"\xff\xd8\xff", media_type="image/jpeg")
        assert estimate_block_tokens(block) == 1000

    def test_png_header_parsing(self) -> None:
        data = _make_png_header(width=600, height=450)
        block = ImageBlock(data=data, media_type="image/png")
        # 600 * 450 / 750 = 360
        assert estimate_block_tokens(block) == 360

    def test_audio_with_duration(self) -> None:
        block = AudioBlock(data=b"", media_type="audio/mp3", duration_seconds=60)
        # 60 * 25 = 1500
        assert estimate_block_tokens(block) == 1500

    def test_audio_without_duration_size_based(self) -> None:
        block = AudioBlock(data=b"\x00" * 160_000, media_type="audio/mp3")
        # 160000 / 16000 * 25 = 250
        assert estimate_block_tokens(block) == 250

    def test_structured_output_estimation(self) -> None:
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        block = StructuredOutputBlock(schema=schema)
        expected = max(1, int(len(json.dumps(schema)) / 4.0))
        assert estimate_block_tokens(block) == expected

    def test_tool_result_sums_nested(self) -> None:
        block = ToolResultBlock(
            tool_use_id="t1",
            content=[TextBlock(text="a" * 40), TextBlock(text="b" * 40)],
        )
        # Each text: 10 tokens → total 20
        assert estimate_block_tokens(block) == 20


class TestEstimateBlocksTokens:
    def test_sum_of_blocks(self) -> None:
        blocks: list[ContentBlock] = [
            TextBlock(text="a" * 400),
            TextBlock(text="b" * 200),
        ]
        assert estimate_blocks_tokens(blocks) == 150


# ── validate_content_blocks (list) ──


class TestValidateContentBlocks:
    def test_mixed_valid_blocks_pass(self) -> None:
        blocks: list[ContentBlock] = [
            TextBlock(text="hello"),
            ImageBlock(data=_make_png_header(), media_type="image/png"),
        ]
        validate_content_blocks(blocks)

    def test_one_invalid_raises(self) -> None:
        blocks: list[ContentBlock] = [
            TextBlock(text="ok"),
            ImageBlock(data=b"", media_type="image/bmp"),
        ]
        with pytest.raises(ContentBlockValidationError):
            validate_content_blocks(blocks)


# ── Config integration ──


class TestConfigIntegration:
    def test_config_defaults(self) -> None:
        from app.core.config import AIConfig

        config = AIConfig()
        assert config.max_image_size_mb == 20
        assert config.max_audio_duration_s == 300
        assert "image/png" in config.supported_image_types
        assert len(config.supported_image_types) == 4


# ── Schema round-trip ──


class TestSchemaRoundTrip:
    def test_text_block_round_trip(self) -> None:
        from app.ai.multimodal_schemas import block_to_schema, schema_to_block

        original = TextBlock(text="hello world")
        schema = block_to_schema(original)
        restored = schema_to_block(schema)
        assert isinstance(restored, TextBlock)
        assert restored.text == original.text

    def test_image_block_round_trip(self) -> None:
        from app.ai.multimodal_schemas import block_to_schema, schema_to_block

        original = ImageBlock(
            data=_make_png_header(),
            media_type="image/png",
            width=100,
            height=100,
        )
        schema = block_to_schema(original)
        restored = schema_to_block(schema)
        assert isinstance(restored, ImageBlock)
        assert restored.data == original.data
        assert restored.media_type == original.media_type
        assert restored.width == original.width

    def test_audio_block_round_trip(self) -> None:
        from app.ai.multimodal_schemas import block_to_schema, schema_to_block

        original = AudioBlock(data=b"\xff\xfb\x00\x00", media_type="audio/mp3", duration_seconds=60)
        schema = block_to_schema(original)
        restored = schema_to_block(schema)
        assert isinstance(restored, AudioBlock)
        assert restored.data == original.data
        assert restored.duration_seconds == original.duration_seconds

    def test_structured_output_round_trip(self) -> None:
        from app.ai.multimodal_schemas import block_to_schema, schema_to_block

        original = StructuredOutputBlock(
            schema={"type": "object", "properties": {"name": {"type": "string"}}},
            name="test_schema",
            strict=False,
        )
        schema = block_to_schema(original)
        restored = schema_to_block(schema)
        assert isinstance(restored, StructuredOutputBlock)
        assert restored.schema == original.schema
        assert restored.name == original.name
        assert restored.strict == original.strict

    def test_tool_result_round_trip(self) -> None:
        from app.ai.multimodal_schemas import block_to_schema, schema_to_block

        original = ToolResultBlock(
            tool_use_id="abc-123",
            content=[TextBlock(text="tool output")],
        )
        schema = block_to_schema(original)
        restored = schema_to_block(schema)
        assert isinstance(restored, ToolResultBlock)
        assert restored.tool_use_id == original.tool_use_id
        assert len(restored.content) == 1
        assert isinstance(restored.content[0], TextBlock)
        assert restored.content[0].text == "tool output"
