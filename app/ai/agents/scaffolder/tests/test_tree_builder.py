"""Tests for scaffolder tree mode (Phase 48.7).

Covers TreeBuilder, slot type inference, pipeline.execute_tree(),
and service routing.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.scaffolder.pipeline import PipelineError, ScaffolderPipeline
from app.ai.agents.scaffolder.tree_builder import (
    ComponentSelection,
    TreeBuilder,
    _infer_slot_value,
)
from app.ai.protocols import CompletionResponse
from app.components.tree_schema import (
    ButtonSlot,
    ImageSlot,
    TextSlot,
)

# ── Fixtures ──


def _make_manifest() -> tuple[set[str], dict[str, list[dict[str, Any]]]]:
    """Minimal manifest for testing."""
    slugs = {"hero-full-width", "text-block", "button", "footer-basic"}
    slot_defs: dict[str, list[dict[str, Any]]] = {
        "hero-full-width": [
            {"slot_id": "heading", "slot_type": "content", "required": True},
            {"slot_id": "hero_image", "slot_type": "image", "required": False},
            {"slot_id": "cta_url", "slot_type": "cta", "required": False},
        ],
        "text-block": [
            {"slot_id": "body_text", "slot_type": "content", "required": True},
        ],
        "button": [
            {"slot_id": "cta_text", "slot_type": "cta", "required": True},
        ],
        "footer-basic": [
            {"slot_id": "footer_text", "slot_type": "content", "required": False},
        ],
    }
    return slugs, slot_defs


def _make_design_tokens() -> dict[str, dict[str, str]]:
    return {
        "colors": {"primary": "#FF6B35", "background": "#FFFFFF", "text": "#333333"},
        "fonts": {"body": "Arial, sans-serif", "heading": "Georgia, serif"},
    }


# ── Group 1: TreeBuilder.build() ──


class TestTreeBuilderBuild:
    def test_build_basic_tree(self) -> None:
        """3 sections (hero, text-block, button) → valid EmailTree."""
        slugs, slot_defs = _make_manifest()
        builder = TreeBuilder(slugs, slot_defs)

        selections = [
            ComponentSelection("hero-full-width", "Full-width hero"),
            ComponentSelection("text-block", "Body copy"),
            ComponentSelection("button", "Primary CTA"),
        ]
        fills = {
            0: {"heading": TextSlot(text="Welcome!")},
            1: {"body_text": TextSlot(text="Hello world")},
            2: {
                "cta_text": ButtonSlot(
                    text="Shop", href="#", bg_color="#000000", text_color="#FFFFFF"
                )
            },
        }

        tree = builder.build(
            component_selections=selections,
            slot_fills_by_section=fills,
            design_tokens=_make_design_tokens(),
            subject="Test Email",
            preheader="Preview text",
        )

        assert len(tree.sections) == 3
        assert tree.sections[0].component_slug == "hero-full-width"
        assert tree.sections[1].component_slug == "text-block"
        assert tree.sections[2].component_slug == "button"
        assert tree.metadata.subject == "Test Email"
        assert tree.metadata.preheader == "Preview text"

    def test_build_tree_design_tokens_propagated(self) -> None:
        """DesignTokens → TreeMetadata.design_tokens."""
        slugs, slot_defs = _make_manifest()
        builder = TreeBuilder(slugs, slot_defs)
        tokens = _make_design_tokens()

        tree = builder.build(
            component_selections=[ComponentSelection("text-block")],
            slot_fills_by_section={0: {"body_text": TextSlot(text="Content")}},
            design_tokens=tokens,
            subject="Test",
            preheader="",
        )

        assert tree.metadata.design_tokens == tokens
        assert tree.metadata.design_tokens["colors"]["primary"] == "#FF6B35"

    def test_build_tree_unknown_slug_falls_back_to_custom(self) -> None:
        """Unknown slug → __custom__ with comment."""
        slugs, slot_defs = _make_manifest()
        builder = TreeBuilder(slugs, slot_defs)

        tree = builder.build(
            component_selections=[ComponentSelection("nonexistent-widget")],
            slot_fills_by_section={0: {}},
            design_tokens=_make_design_tokens(),
            subject="Test",
            preheader="",
        )

        assert tree.sections[0].component_slug == "__custom__"
        assert tree.sections[0].custom_html is not None
        assert "nonexistent-widget" in tree.sections[0].custom_html

    def test_build_tree_validates_against_manifest(self) -> None:
        """Known slugs + wrong slot names → validation warnings (tree still returned)."""
        slugs, slot_defs = _make_manifest()
        builder = TreeBuilder(slugs, slot_defs)

        # 'bad_slot' is not defined for hero-full-width
        tree = builder.build(
            component_selections=[ComponentSelection("hero-full-width")],
            slot_fills_by_section={0: {"bad_slot": TextSlot(text="oops")}},
            design_tokens=_make_design_tokens(),
            subject="Test",
            preheader="",
        )

        # Tree should still be returned (validation is warning-only)
        assert len(tree.sections) == 1
        assert tree.sections[0].component_slug == "hero-full-width"


# ── Group 2: Slot type inference ──


class TestSlotTypeInference:
    def test_infer_text_slot(self) -> None:
        """Plain text → TextSlot."""
        result = _infer_slot_value("heading", "Welcome to our store", "content")
        assert isinstance(result, TextSlot)
        assert result.text == "Welcome to our store"

    def test_infer_image_slot(self) -> None:
        """URL with .png + slot_type='image' → ImageSlot."""
        result = _infer_slot_value("hero_image", "https://cdn.example.com/hero.png", "image")
        assert isinstance(result, ImageSlot)
        assert result.src == "https://cdn.example.com/hero.png"

    def test_infer_button_slot(self) -> None:
        """CTA slot_type → ButtonSlot."""
        result = _infer_slot_value("cta_url", "Shop Now", "cta")
        assert isinstance(result, ButtonSlot)
        assert result.text == "Shop Now"

    def test_infer_from_dict_with_type(self) -> None:
        """Dict with 'type' field → parsed directly."""
        result = _infer_slot_value(
            "hero_image",
            {"type": "image", "src": "https://img.jpg", "alt": "Hero", "width": 600, "height": 300},
            "content",
        )
        assert isinstance(result, ImageSlot)
        assert result.src == "https://img.jpg"


# ── Group 3: Pipeline.execute_tree() ──


class TestPipelineExecuteTree:
    @pytest.fixture()
    def mock_provider(self) -> AsyncMock:
        return AsyncMock()

    @pytest.mark.asyncio()
    async def test_execute_tree_3_pass(self, mock_provider: AsyncMock) -> None:
        """Mock 3 LLM calls → valid EmailTree returned."""
        layout_response = json.dumps(
            {
                "sections": [
                    {"component_slug": "hero-full-width", "rationale": "Hero"},
                    {"component_slug": "text-block", "rationale": "Body"},
                ],
                "subject": "Summer Sale",
                "preheader": "Don't miss out",
            }
        )
        content_response = json.dumps(
            {
                "sections": [
                    {
                        "index": 0,
                        "fills": {"heading": {"type": "text", "text": "Summer Sale!"}},
                    },
                    {
                        "index": 1,
                        "fills": {"body_text": {"type": "text", "text": "Great deals"}},
                    },
                ],
            }
        )
        design_response = json.dumps(
            {
                "colors": {"primary": "#FF6B35", "background": "#FFFFFF"},
                "fonts": {"body": "Arial", "heading": "Georgia"},
                "button_style": "filled",
            }
        )

        mock_provider.complete = AsyncMock(
            side_effect=[
                CompletionResponse(content=layout_response, model="test", usage={}),
                CompletionResponse(content=content_response, model="test", usage={}),
                CompletionResponse(content=design_response, model="test", usage={}),
            ]
        )

        pipeline = ScaffolderPipeline(mock_provider, "test-model")

        with patch(
            "app.ai.agents.scaffolder.tree_builder._build_manifest_index",
            return_value=(
                frozenset({"hero-full-width", "text-block", "button", "footer-basic"}),
                {
                    "hero-full-width": [
                        {"slot_id": "heading", "slot_type": "content", "required": True},
                    ],
                    "text-block": [
                        {"slot_id": "body_text", "slot_type": "content", "required": True},
                    ],
                },
            ),
        ):
            tree = await pipeline.execute_tree("Create a summer sale email")

        assert tree.metadata.subject == "Summer Sale"
        assert len(tree.sections) == 2
        assert tree.sections[0].component_slug == "hero-full-width"

    @pytest.mark.asyncio()
    async def test_execute_tree_parallel_content_design(self, mock_provider: AsyncMock) -> None:
        """Passes 2+3 run concurrently — both complete."""
        layout_response = json.dumps(
            {
                "sections": [{"component_slug": "text-block", "rationale": "Body"}],
                "subject": "Test",
                "preheader": "",
            }
        )
        content_response = json.dumps(
            {"sections": [{"index": 0, "fills": {"body_text": {"type": "text", "text": "Hi"}}}]}
        )
        design_response = json.dumps(
            {"colors": {"primary": "#000"}, "fonts": {"body": "Arial"}, "button_style": "filled"}
        )

        mock_provider.complete = AsyncMock(
            side_effect=[
                CompletionResponse(content=layout_response, model="test", usage={}),
                CompletionResponse(content=content_response, model="test", usage={}),
                CompletionResponse(content=design_response, model="test", usage={}),
            ]
        )

        pipeline = ScaffolderPipeline(mock_provider, "test-model")

        with patch(
            "app.ai.agents.scaffolder.tree_builder._build_manifest_index",
            return_value=(
                frozenset({"text-block"}),
                {
                    "text-block": [
                        {"slot_id": "body_text", "slot_type": "content", "required": True}
                    ]
                },
            ),
        ):
            tree = await pipeline.execute_tree("Simple email")

        # All 3 calls made (1 layout + 1 content + 1 design)
        assert mock_provider.complete.call_count == 3
        assert len(tree.sections) == 1

    @pytest.mark.asyncio()
    async def test_execute_tree_llm_error_raises_pipeline_error(
        self, mock_provider: AsyncMock
    ) -> None:
        """LLM failure → PipelineError."""
        # Return invalid JSON that fails parsing
        mock_provider.complete = AsyncMock(
            side_effect=[
                CompletionResponse(content="not json", model="test", usage={}),
                CompletionResponse(content="still not json", model="test", usage={}),
            ]
        )

        pipeline = ScaffolderPipeline(mock_provider, "test-model")

        with (
            patch(
                "app.ai.agents.scaffolder.tree_builder._build_manifest_index",
                return_value=(frozenset({"text-block"}), {}),
            ),
            pytest.raises(PipelineError, match="Failed to parse JSON"),
        ):
            await pipeline.execute_tree("Test brief for error handling")


# ── Group 4: Service integration ──


class TestServiceTreeMode:
    @pytest.mark.asyncio()
    async def test_service_tree_mode_returns_tree_response(self) -> None:
        """output_mode='tree' → response has tree dict, html=''."""
        from app.ai.agents.scaffolder.schemas import ScaffolderRequest, ScaffolderResponse
        from app.ai.agents.scaffolder.service import ScaffolderService

        service = ScaffolderService()

        # Mock the entire _process_tree method to return a known response
        mock_tree = {
            "metadata": {"subject": "Test", "preheader": "", "design_tokens": {}},
            "sections": [{"component_slug": "text-block", "slot_fills": {}}],
        }

        with patch.object(
            service,
            "_process_tree",
            new_callable=AsyncMock,
            return_value=ScaffolderResponse(
                html="",
                tree=mock_tree,
                model="test:model",
                confidence=0.9,
            ),
        ):
            req = ScaffolderRequest(
                brief="A simple promotional email about summer sale",
                output_mode="tree",
            )
            result = await service._process_structured(req)

        assert result.html == ""
        assert result.tree is not None
        assert result.tree["metadata"]["subject"] == "Test"

    @pytest.mark.asyncio()
    async def test_service_html_mode_unchanged(self) -> None:
        """output_mode='structured' → response has html, no tree (regression)."""
        from app.ai.agents.scaffolder.schemas import ScaffolderRequest
        from app.ai.agents.scaffolder.service import ScaffolderService

        service = ScaffolderService()

        with (
            patch("app.ai.agents.scaffolder.service.get_settings") as mock_settings,
            patch("app.ai.agents.scaffolder.service.resolve_model", return_value="test-model"),
            patch("app.ai.agents.scaffolder.service.get_registry") as mock_registry,
            patch.object(ScaffolderPipeline, "execute", new_callable=AsyncMock) as mock_execute,
            patch(
                "app.ai.agents.scaffolder.service.sanitize_html_xss",
                side_effect=lambda html, **_kw: html,
            ),
        ):
            mock_settings.return_value = MagicMock(
                ai=MagicMock(provider="test"),
                knowledge=MagicMock(crag_enabled=False),
            )
            mock_registry.return_value = MagicMock()

            from app.ai.agents.schemas.build_plan import (
                DesignTokens,
                EmailBuildPlan,
                TemplateSelection,
            )

            mock_execute.return_value = EmailBuildPlan(
                template=TemplateSelection(template_name="test", reasoning="test"),
                slot_fills=(),
                design_tokens=DesignTokens(
                    colors={"primary": "#000", "background": "#fff", "text": "#333"},
                    fonts={"body": "Arial", "heading": "Georgia"},
                ),
            )

            with patch("app.ai.agents.scaffolder.service.TemplateAssembler") as mock_assembler_cls:
                mock_assembler_cls.return_value.assemble.return_value = (
                    "<table><tr><td>Hello</td></tr></table>"
                )

                req = ScaffolderRequest(
                    brief="A simple promotional email about summer sale items",
                    output_mode="structured",
                )
                result = await service._process_structured(req)

        assert result.html != ""
        assert result.tree is None
