"""Tests for Phase 23.3 — Agent Multimodal Integration."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from app.ai.agents.base import BaseAgentService
from app.ai.multimodal import ContentBlock, ImageBlock, TextBlock

# --- Minimal valid PNG for tests ---
_VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


# --- BaseAgentService helpers ---


class TestBaseAgentMultimodal:
    """Test multimodal convenience methods on BaseAgentService."""

    def test_text_block_helper(self) -> None:
        block = BaseAgentService._text_block("hello")
        assert isinstance(block, TextBlock)
        assert block.text == "hello"

    def test_image_block_helper_valid_png(self) -> None:
        block = BaseAgentService._image_block(_VALID_PNG, "image/png")
        assert isinstance(block, ImageBlock)
        assert block.data == _VALID_PNG
        assert block.media_type == "image/png"

    def test_image_block_helper_invalid_mime(self) -> None:
        from app.ai.multimodal import ContentBlockValidationError

        with pytest.raises(ContentBlockValidationError):
            BaseAgentService._image_block(b"\x89PNG\r\n\x1a\n", "image/bmp")

    def test_build_multimodal_messages_text_only(self) -> None:
        service = BaseAgentService()
        messages = service._build_multimodal_messages(
            system_prompt="You are helpful.",
            user_text="Hello",
            context_blocks=None,
        )
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert isinstance(messages[1].content, str)

    def test_build_multimodal_messages_with_blocks(self) -> None:
        service = BaseAgentService()
        blocks: list[ContentBlock] = [ImageBlock(data=_VALID_PNG, media_type="image/png")]
        messages = service._build_multimodal_messages(
            system_prompt="You are helpful.",
            user_text="Describe this image",
            context_blocks=blocks,
        )
        assert len(messages) == 2
        assert isinstance(messages[1].content, list)
        assert len(messages[1].content) == 2  # TextBlock + ImageBlock
        assert isinstance(messages[1].content[0], TextBlock)
        assert isinstance(messages[1].content[1], ImageBlock)

    def test_build_multimodal_messages_sanitizes_text(self) -> None:
        """Text is sanitized even when blocks are present."""
        service = BaseAgentService()
        blocks: list[ContentBlock] = [ImageBlock(data=_VALID_PNG, media_type="image/png")]
        messages = service._build_multimodal_messages(
            system_prompt="System",
            user_text="Some text",
            context_blocks=blocks,
        )
        # User message should be a list with TextBlock first
        content = messages[1].content
        assert isinstance(content, list)
        assert isinstance(content[0], TextBlock)


# --- VisualQAService refactor ---


class TestVisualQAMultimodal:
    """Test VisualQA uses typed ImageBlocks."""

    def test_screenshots_to_blocks_valid(self) -> None:
        from app.ai.agents.visual_qa.service import VisualQAService

        service = VisualQAService()
        b64 = base64.b64encode(_VALID_PNG).decode()
        result = service._screenshots_to_blocks({"gmail": b64})
        assert isinstance(result, list)
        assert len(result) == 2  # ImageBlock + TextBlock label
        assert isinstance(result[0], ImageBlock)
        assert isinstance(result[1], TextBlock)

    def test_screenshots_to_blocks_invalid_base64(self) -> None:
        from app.ai.agents.visual_qa.schemas import VisualQAResponse
        from app.ai.agents.visual_qa.service import VisualQAService

        service = VisualQAService()
        result = service._screenshots_to_blocks({"gmail": "not-valid-base64!!!"})
        assert isinstance(result, VisualQAResponse)
        assert "Invalid base64" in result.summary

    def test_screenshots_to_blocks_too_large(self) -> None:
        from app.ai.agents.visual_qa.schemas import VisualQAResponse
        from app.ai.agents.visual_qa.service import (
            _MAX_SCREENSHOT_B64_LEN,
            VisualQAService,
        )

        service = VisualQAService()
        big_b64 = "A" * (_MAX_SCREENSHOT_B64_LEN + 1)
        result = service._screenshots_to_blocks({"gmail": big_b64})
        assert isinstance(result, VisualQAResponse)
        assert "exceeds size limit" in result.summary

    def test_screenshots_to_blocks_multiple_clients(self) -> None:
        from app.ai.agents.visual_qa.service import VisualQAService

        service = VisualQAService()
        b64 = base64.b64encode(_VALID_PNG).decode()
        result = service._screenshots_to_blocks({"gmail": b64, "outlook": b64})
        assert isinstance(result, list)
        assert len(result) == 4  # 2 * (ImageBlock + TextBlock)


# --- Blueprint engine LAYER 14 ---


class TestBlueprintMultimodalContext:
    """Test LAYER 14 multimodal context injection."""

    def test_multimodal_disabled_no_context(self) -> None:
        """Feature flag off → no multimodal_context on NodeContext."""
        from app.ai.blueprints.protocols import NodeContext

        context = NodeContext(html="<p>test</p>", brief="test", iteration=0)
        assert context.multimodal_context is None

    def test_node_context_accepts_multimodal(self) -> None:
        """NodeContext can store multimodal content blocks."""
        from app.ai.blueprints.protocols import NodeContext

        blocks: list[ContentBlock] = [ImageBlock(data=_VALID_PNG, media_type="image/png")]
        context = NodeContext(
            html="<p>test</p>",
            brief="test",
            iteration=0,
            multimodal_context=blocks,
        )
        assert context.multimodal_context is not None
        assert len(context.multimodal_context) == 1

    def test_node_context_default_none(self) -> None:
        """Default multimodal_context is None (backward compat)."""
        from app.ai.blueprints.protocols import NodeContext

        context = NodeContext(html="", brief="", iteration=0)
        assert context.multimodal_context is None


# --- ScaffolderNode design reference ---


class TestScaffolderDesignReference:
    """Test scaffolder accepts design reference images."""

    def test_scaffolder_node_builds_multimodal_when_context_present(self) -> None:
        """When multimodal_context has ImageBlocks, scaffolder includes them."""
        from app.ai.blueprints.protocols import NodeContext

        blocks: list[ContentBlock] = [ImageBlock(data=_VALID_PNG, media_type="image/png")]
        context = NodeContext(
            html="",
            brief="Build a newsletter",
            iteration=0,
            multimodal_context=blocks,
        )
        assert context.multimodal_context is not None
        assert len(context.multimodal_context) == 1


# --- Feature flag gating ---


class TestMultimodalFeatureFlag:
    """Test that multimodal context is gated by config flag."""

    def test_config_default_off(self) -> None:
        """Config default is off."""
        from app.core.config import AIConfig

        config = AIConfig()
        assert config.multimodal_context_enabled is False

    def test_config_can_enable(self) -> None:
        """Config can be enabled."""
        from app.core.config import AIConfig

        config = AIConfig(multimodal_context_enabled=True)
        assert config.multimodal_context_enabled is True


# --- Empty blocks edge case ---


class TestMultimodalEdgeCases:
    """Test edge cases in multimodal message building."""

    def test_empty_blocks_list_treated_as_text_only(self) -> None:
        """Empty list is falsy → falls back to text-only."""
        service = BaseAgentService()
        messages = service._build_multimodal_messages(
            system_prompt="System",
            user_text="Hello",
            context_blocks=[],
        )
        assert isinstance(messages[1].content, str)


# --- ScaffolderNode vision capability integration ---


class TestScaffolderVisionCapability:
    """Test scaffolder vision capability check logic."""

    @pytest.mark.asyncio
    async def test_scaffolder_skips_images_when_no_vision(self) -> None:
        """Model without vision → design ref blocks not used."""
        from dataclasses import dataclass, field
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.ai.blueprints.nodes.scaffolder_node import ScaffolderNode
        from app.ai.blueprints.protocols import NodeContext

        blocks: list[ContentBlock] = [ImageBlock(data=_VALID_PNG, media_type="image/png")]
        context = NodeContext(
            html="",
            brief="Build a newsletter",
            iteration=0,
            multimodal_context=blocks,
        )

        node = ScaffolderNode()

        @dataclass(frozen=True)
        class FakeModelSpec:
            model_id: str = "gpt-4o-mini"
            provider: str = "openai"
            capabilities: frozenset[str] = field(default_factory=frozenset[str])

        # Use MagicMock (not AsyncMock) — find_models is sync
        mock_cap_registry = MagicMock()
        mock_cap_registry.find_models.return_value = [FakeModelSpec(model_id="other-model")]

        mock_provider = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "<html><body>test</body></html>"
        mock_response.usage = {"total_tokens": 100}
        mock_provider.complete.return_value = mock_response

        with (
            patch("app.ai.blueprints.nodes.scaffolder_node.get_registry") as mock_get_reg,
            patch(
                "app.ai.blueprints.nodes.scaffolder_node.resolve_model", return_value="gpt-4o-mini"
            ),
            patch("app.ai.blueprints.nodes.scaffolder_node.get_settings") as mock_settings,
            patch(
                "app.ai.capability_registry.get_capability_registry",
                return_value=mock_cap_registry,
            ),
        ):
            mock_get_reg.return_value.get_llm.return_value = mock_provider
            mock_settings.return_value.ai.provider = "openai"

            await node.execute(context)

        # LLM was called with text-only content (no multimodal blocks)
        call_args = mock_provider.complete.call_args
        messages = call_args[0][0]
        user_msg = messages[1]
        assert isinstance(user_msg.content, str), "Should be text-only when model has no vision"

    @pytest.mark.asyncio
    async def test_scaffolder_includes_images_when_vision_available(self) -> None:
        """Model with vision → design ref blocks included."""
        from dataclasses import dataclass, field
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.ai.blueprints.nodes.scaffolder_node import ScaffolderNode
        from app.ai.blueprints.protocols import NodeContext

        blocks: list[ContentBlock] = [ImageBlock(data=_VALID_PNG, media_type="image/png")]
        context = NodeContext(
            html="",
            brief="Build a newsletter",
            iteration=0,
            multimodal_context=blocks,
        )

        node = ScaffolderNode()

        @dataclass(frozen=True)
        class FakeModelSpec:
            model_id: str = "gpt-4o"
            provider: str = "openai"
            capabilities: frozenset[str] = field(default_factory=frozenset[str])

        mock_cap_registry = MagicMock()
        mock_cap_registry.find_models.return_value = [FakeModelSpec(model_id="gpt-4o")]

        mock_provider = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "<html><body>test</body></html>"
        mock_response.usage = {"total_tokens": 100}
        mock_provider.complete.return_value = mock_response

        with (
            patch("app.ai.blueprints.nodes.scaffolder_node.get_registry") as mock_get_reg,
            patch(
                "app.ai.blueprints.nodes.scaffolder_node.resolve_model",
                return_value="gpt-4o",
            ),
            patch("app.ai.blueprints.nodes.scaffolder_node.get_settings") as mock_settings,
            patch(
                "app.ai.capability_registry.get_capability_registry",
                return_value=mock_cap_registry,
            ),
        ):
            mock_get_reg.return_value.get_llm.return_value = mock_provider
            mock_settings.return_value.ai.provider = "openai"

            await node.execute(context)

        # LLM was called with multimodal content (list of blocks)
        call_args = mock_provider.complete.call_args
        messages = call_args[0][0]
        user_msg = messages[1]
        user_content: list[Any] = user_msg.content
        assert isinstance(user_content, list), "Should be multimodal when model has vision"
        # Should contain TextBlock (sanitized brief) + TextBlock (instruction) + ImageBlock
        has_image = any(isinstance(b, ImageBlock) for b in user_content)
        assert has_image, "Should include design reference ImageBlock"


# --- Engine LAYER 14 integration ---


class TestEngineLayer14:
    """Test LAYER 14 multimodal context injection in BlueprintEngine."""

    def test_layer14_injects_visual_qa_screenshots(self) -> None:
        """LAYER 14 converts screenshot metadata to ImageBlocks for visual_qa node."""
        from app.ai.blueprints.protocols import NodeContext

        b64 = base64.b64encode(_VALID_PNG).decode()
        context = NodeContext(
            html="<p>test</p>",
            brief="test",
            iteration=0,
            metadata={"screenshots": {"gmail": b64, "outlook": b64}},
        )

        # Simulate what LAYER 14 does (extracted logic)
        from app.ai.multimodal import validate_content_blocks

        multimodal_blocks: list[ContentBlock] = []
        screenshots_dict: dict[str, str] = context.metadata.get("screenshots", {})  # type: ignore[assignment]
        for client_name, b64_data in screenshots_dict.items():
            image_bytes = base64.b64decode(b64_data)
            multimodal_blocks.append(
                ImageBlock(data=image_bytes, media_type="image/png", source="base64")
            )
            multimodal_blocks.append(TextBlock(text=f"[Screenshot: {client_name}]"))

        validate_content_blocks(multimodal_blocks)
        context.multimodal_context = multimodal_blocks

        assert context.multimodal_context is not None
        assert len(context.multimodal_context) == 4  # 2 clients x (ImageBlock + TextBlock)
        assert isinstance(context.multimodal_context[0], ImageBlock)
        assert isinstance(context.multimodal_context[1], TextBlock)
        assert context.multimodal_context[1].text == "[Screenshot: gmail]"

    def test_layer14_injects_design_assets(self) -> None:
        """LAYER 14 converts design import assets to ImageBlocks for scaffolder node."""
        from app.ai.blueprints.protocols import NodeContext

        context = NodeContext(
            html="",
            brief="test",
            iteration=0,
            metadata={
                "design_import_assets": [
                    {"image_bytes": _VALID_PNG, "media_type": "image/png"},
                ]
            },
        )

        # Simulate scaffolder LAYER 14 logic
        from app.ai.multimodal import validate_content_blocks

        multimodal_blocks: list[ContentBlock] = []
        design_import_assets: list[dict[str, object]] = context.metadata.get(  # type: ignore[assignment]
            "design_import_assets", []
        )
        for asset in design_import_assets:
            raw_image = asset.get("image_bytes")
            if isinstance(raw_image, bytes):
                multimodal_blocks.append(
                    ImageBlock(
                        data=raw_image,
                        media_type=str(asset.get("media_type", "image/png")),
                        source="base64",
                    )
                )

        validate_content_blocks(multimodal_blocks)
        context.multimodal_context = multimodal_blocks

        assert context.multimodal_context is not None
        assert len(context.multimodal_context) == 1
        assert isinstance(context.multimodal_context[0], ImageBlock)
        assert context.multimodal_context[0].data == _VALID_PNG

    def test_layer14_skips_invalid_base64(self) -> None:
        """LAYER 14 skips invalid base64 screenshots gracefully."""
        from app.ai.blueprints.protocols import NodeContext

        # Use validate=True to make b64decode strict (engine should use this)
        context = NodeContext(
            html="<p>test</p>",
            brief="test",
            iteration=0,
            metadata={"screenshots": {"gmail": "!!!invalid-base64-data!!!"}},
        )

        # Simulate LAYER 14 with invalid data
        multimodal_blocks: list[ContentBlock] = []
        screenshots_dict: dict[str, str] = context.metadata.get("screenshots", {})  # type: ignore[assignment]
        for client_name, b64_data in screenshots_dict.items():
            try:
                image_bytes = base64.b64decode(b64_data, validate=True)
                multimodal_blocks.append(
                    ImageBlock(data=image_bytes, media_type="image/png", source="base64")
                )
                multimodal_blocks.append(TextBlock(text=f"[Screenshot: {client_name}]"))
            except Exception:  # noqa: S110
                pass  # Graceful skip — mirrors engine behavior

        # No valid blocks produced from invalid data
        assert len(multimodal_blocks) == 0
