"""Tests for the 3-pass scaffolder pipeline and template assembler."""

import json
from unittest.mock import AsyncMock

import pytest

from app.ai.agents.scaffolder.assembler import AssemblyError, TemplateAssembler
from app.ai.agents.scaffolder.pipeline import PipelineError, ScaffolderPipeline, _parse_json
from app.ai.agents.schemas.build_plan import (
    DesignTokens,
    EmailBuildPlan,
    SectionDecision,
    SlotFill,
    TemplateSelection,
)
from app.ai.protocols import CompletionResponse
from app.ai.templates import GoldenTemplate, TemplateMetadata, TemplateSlot
from app.ai.templates.registry import TemplateRegistry

# ── _parse_json ──


class TestParseJson:
    def test_raw_json(self) -> None:
        assert _parse_json('{"key": "value"}') == {"key": "value"}

    def test_code_fenced_json(self) -> None:
        assert _parse_json('```json\n{"key": "value"}\n```') == {"key": "value"}

    def test_embedded_json(self) -> None:
        assert _parse_json('Here is the result: {"key": "value"} done') == {"key": "value"}

    def test_invalid_returns_none(self) -> None:
        assert _parse_json("not json at all") is None


# ── TemplateAssembler ──


class TestTemplateAssembler:
    @pytest.fixture()
    def registry(self) -> TemplateRegistry:
        reg = TemplateRegistry.__new__(TemplateRegistry)
        reg._templates = {}
        reg._loaded = True
        return reg

    @pytest.fixture()
    def sample_template(self) -> GoldenTemplate:
        return GoldenTemplate(
            metadata=TemplateMetadata(
                name="test_template",
                display_name="Test Template",
                layout_type="newsletter",
                column_count=1,
                has_hero_image=True,
                has_navigation=False,
                has_social_links=False,
                sections=("header", "body", "footer"),
                ideal_for=("testing",),
                description="A test template",
            ),
            html=(
                '<div data-section="header"><h1 data-slot="headline">Placeholder</h1></div>'
                '<div data-section="body"><p data-slot="body_text">Body placeholder</p></div>'
                '<div data-slot="preheader" style="display:none;">Preview</div>'
            ),
            slots=(
                TemplateSlot(
                    slot_id="headline",
                    slot_type="headline",
                    selector="[data-slot='headline']",
                    max_chars=80,
                ),
                TemplateSlot(
                    slot_id="body_text",
                    slot_type="body",
                    selector="[data-slot='body_text']",
                ),
                TemplateSlot(
                    slot_id="preheader",
                    slot_type="preheader",
                    selector="[data-slot='preheader']",
                    required=False,
                ),
            ),
        )

    def test_assemble_fills_slots(
        self, registry: TemplateRegistry, sample_template: GoldenTemplate
    ) -> None:
        registry._templates["test_template"] = sample_template
        assembler = TemplateAssembler(registry=registry)

        plan = EmailBuildPlan(
            template=TemplateSelection(template_name="test_template", reasoning="test"),
            slot_fills=(
                SlotFill(slot_id="headline", content="Welcome!"),
                SlotFill(slot_id="body_text", content="Hello world"),
            ),
            design_tokens=DesignTokens(
                primary_color="#ff0000",
                secondary_color="#00ff00",
                background_color="#ffffff",
                text_color="#333333",
                font_family="Arial,sans-serif",
                heading_font_family="Georgia,serif",
            ),
        )

        html = assembler.assemble(plan)
        assert "Welcome!" in html
        assert "Hello world" in html
        assert "Placeholder" not in html
        assert "Body placeholder" not in html

    def test_assemble_missing_template_raises(self, registry: TemplateRegistry) -> None:
        assembler = TemplateAssembler(registry=registry)
        plan = EmailBuildPlan(
            template=TemplateSelection(template_name="nonexistent", reasoning="test"),
            slot_fills=(),
            design_tokens=DesignTokens(
                primary_color="#000",
                secondary_color="#000",
                background_color="#fff",
                text_color="#333",
                font_family="Arial",
                heading_font_family="Georgia",
            ),
        )
        with pytest.raises(AssemblyError, match="not found"):
            assembler.assemble(plan)

    def test_assemble_uses_fallback_template(
        self, registry: TemplateRegistry, sample_template: GoldenTemplate
    ) -> None:
        registry._templates["test_template"] = sample_template
        assembler = TemplateAssembler(registry=registry)

        plan = EmailBuildPlan(
            template=TemplateSelection(
                template_name="nonexistent",
                reasoning="test",
                fallback_template="test_template",
            ),
            slot_fills=(SlotFill(slot_id="headline", content="Fallback!"),),
            design_tokens=DesignTokens(
                primary_color="#000",
                secondary_color="#000",
                background_color="#fff",
                text_color="#333",
                font_family="Arial",
                heading_font_family="Georgia",
            ),
        )

        html = assembler.assemble(plan)
        assert "Fallback!" in html

    def test_assemble_hides_section(
        self, registry: TemplateRegistry, sample_template: GoldenTemplate
    ) -> None:
        registry._templates["test_template"] = sample_template
        assembler = TemplateAssembler(registry=registry)

        plan = EmailBuildPlan(
            template=TemplateSelection(template_name="test_template", reasoning="test"),
            slot_fills=(),
            design_tokens=DesignTokens(
                primary_color="#000",
                secondary_color="#000",
                background_color="#fff",
                text_color="#333",
                font_family="Arial",
                heading_font_family="Georgia",
            ),
            sections=(SectionDecision(section_name="header", hidden=True),),
        )

        html = assembler.assemble(plan)
        assert 'data-section="header"' not in html
        assert 'data-section="body"' in html

    def test_assemble_sets_preheader(
        self, registry: TemplateRegistry, sample_template: GoldenTemplate
    ) -> None:
        registry._templates["test_template"] = sample_template
        assembler = TemplateAssembler(registry=registry)

        plan = EmailBuildPlan(
            template=TemplateSelection(template_name="test_template", reasoning="test"),
            slot_fills=(),
            design_tokens=DesignTokens(
                primary_color="#000",
                secondary_color="#000",
                background_color="#fff",
                text_color="#333",
                font_family="Arial",
                heading_font_family="Georgia",
            ),
            preheader_text="Check out our sale!",
        )

        html = assembler.assemble(plan)
        assert "Check out our sale!" in html
        assert "Preview" not in html

    def test_assemble_compose_mode(self, registry: TemplateRegistry) -> None:
        """__compose__ template name delegates to TemplateComposer."""
        assembler = TemplateAssembler(registry=registry)

        plan = EmailBuildPlan(
            template=TemplateSelection(
                template_name="__compose__",
                reasoning="Novel layout",
                section_order=("hero_image", "content_1col", "cta_button", "footer_standard"),
                fallback_template=None,
            ),
            slot_fills=(
                SlotFill(slot_id="hero_image_headline", content="Welcome!"),
                SlotFill(slot_id="content_1col_body", content="Body text here"),
            ),
            design_tokens=DesignTokens(
                primary_color="#000",
                secondary_color="#000",
                background_color="#fff",
                text_color="#333",
                font_family="Arial",
                heading_font_family="Georgia",
            ),
        )

        html = assembler.assemble(plan)
        assert "<!DOCTYPE html>" in html
        assert "Welcome!" in html
        assert "Body text here" in html

    def test_assemble_compose_fallback_on_unknown_section(
        self, registry: TemplateRegistry, sample_template: GoldenTemplate
    ) -> None:
        """Composition with unknown sections falls back to fallback_template."""
        registry._templates["test_template"] = sample_template
        assembler = TemplateAssembler(registry=registry)

        plan = EmailBuildPlan(
            template=TemplateSelection(
                template_name="__compose__",
                reasoning="Novel layout",
                section_order=("hero_image", "nonexistent_block"),
                fallback_template="test_template",
            ),
            slot_fills=(SlotFill(slot_id="headline", content="Fallback!"),),
            design_tokens=DesignTokens(
                primary_color="#000",
                secondary_color="#000",
                background_color="#fff",
                text_color="#333",
                font_family="Arial",
                heading_font_family="Georgia",
            ),
        )

        html = assembler.assemble(plan)
        assert "Fallback!" in html

    def test_assemble_compose_empty_section_order_raises(self, registry: TemplateRegistry) -> None:
        """Composition with empty section_order raises AssemblyError."""
        assembler = TemplateAssembler(registry=registry)

        plan = EmailBuildPlan(
            template=TemplateSelection(
                template_name="__compose__",
                reasoning="Novel layout",
                section_order=(),
            ),
            slot_fills=(),
            design_tokens=DesignTokens(
                primary_color="#000",
                secondary_color="#000",
                background_color="#fff",
                text_color="#333",
                font_family="Arial",
                heading_font_family="Georgia",
            ),
        )

        with pytest.raises(AssemblyError, match="non-empty section_order"):
            assembler.assemble(plan)

    def test_assemble_preserves_dollar_signs(
        self, registry: TemplateRegistry, sample_template: GoldenTemplate
    ) -> None:
        """Verify the re.escape bug fix — dollar signs in content preserved."""
        registry._templates["test_template"] = sample_template
        assembler = TemplateAssembler(registry=registry)

        plan = EmailBuildPlan(
            template=TemplateSelection(template_name="test_template", reasoning="test"),
            slot_fills=(SlotFill(slot_id="headline", content="Save $100 today!"),),
            design_tokens=DesignTokens(
                primary_color="#000",
                secondary_color="#000",
                background_color="#fff",
                text_color="#333",
                font_family="Arial",
                heading_font_family="Georgia",
            ),
        )

        html = assembler.assemble(plan)
        assert "Save $100 today!" in html
        assert "\\$" not in html


# ── ScaffolderPipeline ──


class TestScaffolderPipeline:
    @pytest.fixture()
    def mock_provider(self) -> AsyncMock:
        """Provider that returns valid JSON for each pass."""
        provider = AsyncMock()

        layout_response = json.dumps(
            {
                "template_name": "newsletter_1col",
                "reasoning": "Single column fits a welcome email",
                "fallback_template": "minimal_text",
                "section_decisions": [
                    {"section_name": "header", "hidden": False},
                    {"section_name": "body", "hidden": False},
                ],
            }
        )
        content_response = json.dumps(
            {
                "slot_fills": [
                    {"slot_id": "headline", "content": "Welcome!", "is_personalisable": True},
                    {
                        "slot_id": "body_text",
                        "content": "Thanks for joining.",
                        "is_personalisable": False,
                    },
                ],
            }
        )
        design_response = json.dumps(
            {
                "primary_color": "#e84e0f",
                "secondary_color": "#0c2340",
                "background_color": "#ffffff",
                "text_color": "#333333",
                "font_family": "Arial,sans-serif",
                "heading_font_family": "Georgia,serif",
                "border_radius": "4px",
                "button_style": "filled",
            }
        )

        provider.complete.side_effect = [
            CompletionResponse(content=layout_response, model="test"),
            CompletionResponse(content=content_response, model="test"),
            CompletionResponse(content=design_response, model="test"),
        ]
        return provider

    @pytest.fixture()
    def registry(self) -> TemplateRegistry:
        reg = TemplateRegistry.__new__(TemplateRegistry)
        reg._templates = {
            "newsletter_1col": GoldenTemplate(
                metadata=TemplateMetadata(
                    name="newsletter_1col",
                    display_name="Newsletter 1-Col",
                    layout_type="newsletter",
                    column_count=1,
                    has_hero_image=True,
                    has_navigation=False,
                    has_social_links=False,
                    sections=("header", "body"),
                    ideal_for=("digest",),
                    description="Simple newsletter",
                ),
                html='<h1 data-slot="headline">Title</h1><p data-slot="body_text">Body</p>',
                slots=(
                    TemplateSlot(
                        slot_id="headline",
                        slot_type="headline",
                        selector="[data-slot='headline']",
                    ),
                    TemplateSlot(
                        slot_id="body_text",
                        slot_type="body",
                        selector="[data-slot='body_text']",
                    ),
                ),
            ),
        }
        reg._loaded = True
        return reg

    @pytest.mark.asyncio()
    async def test_pipeline_executes_3_passes(
        self, mock_provider: AsyncMock, registry: TemplateRegistry
    ) -> None:
        pipeline = ScaffolderPipeline(mock_provider, "test-model", registry=registry)
        plan = await pipeline.execute("Create a welcome email")

        assert plan.template.template_name == "newsletter_1col"
        assert len(plan.slot_fills) == 2
        assert plan.design_tokens.primary_color == "#e84e0f"
        assert mock_provider.complete.call_count == 3

    @pytest.mark.asyncio()
    async def test_pipeline_retries_on_bad_json(self, registry: TemplateRegistry) -> None:
        provider = AsyncMock()
        provider.complete.side_effect = [
            # First attempt: bad JSON
            CompletionResponse(content="Here's what I think...", model="test"),
            # Retry: valid JSON
            CompletionResponse(
                content=json.dumps(
                    {
                        "template_name": "newsletter_1col",
                        "reasoning": "test",
                        "section_decisions": [],
                    }
                ),
                model="test",
            ),
            # Content pass
            CompletionResponse(
                content=json.dumps({"slot_fills": [{"slot_id": "headline", "content": "Hi"}]}),
                model="test",
            ),
            # Design pass
            CompletionResponse(
                content=json.dumps(
                    {
                        "primary_color": "#000",
                        "secondary_color": "#000",
                        "background_color": "#fff",
                        "text_color": "#333",
                        "font_family": "Arial",
                        "heading_font_family": "Georgia",
                    }
                ),
                model="test",
            ),
        ]

        pipeline = ScaffolderPipeline(provider, "test-model", registry=registry)
        plan = await pipeline.execute("Create a welcome email")

        assert plan.template.template_name == "newsletter_1col"
        # 4 calls: bad + retry + content + design
        assert provider.complete.call_count == 4

    @pytest.mark.asyncio()
    async def test_pipeline_raises_on_persistent_bad_json(self, registry: TemplateRegistry) -> None:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content="I cannot produce JSON", model="test"
        )

        pipeline = ScaffolderPipeline(provider, "test-model", registry=registry)

        with pytest.raises(PipelineError, match="Failed to parse JSON"):
            await pipeline.execute("Create a welcome email")
