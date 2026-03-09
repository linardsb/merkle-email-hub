"""Integration tests for the campaign blueprint with mocked LLM."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.blueprints.definitions.campaign import build_campaign_blueprint
from app.ai.blueprints.engine import BlueprintEngine
from app.ai.protocols import CompletionResponse


class TestCampaignBlueprint:
    """Tests for the full campaign blueprint graph."""

    @pytest.fixture
    def valid_html_response(self) -> CompletionResponse:
        """LLM response with valid HTML that passes QA checks."""
        return CompletionResponse(
            content=(
                "```html\n"
                '<!DOCTYPE html>\n<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" '
                'xmlns:o="urn:schemas-microsoft-com:office:office">\n<head>\n'
                '<meta name="color-scheme" content="light dark">\n'
                "<style>\n"
                "@media (prefers-color-scheme: dark) { .dark-bg { background-color: #1a1a1a; } }\n"
                "[data-ogsc] .dark-bg { background-color: #1a1a1a; }\n"
                "</style>\n"
                "<!--[if mso]><xml><o:OfficeDocumentSettings>"
                "<o:PixelsPerInch>96</o:PixelsPerInch>"
                "</o:OfficeDocumentSettings></xml><![endif]-->\n"
                "</head>\n<body>\n"
                '<table role="presentation" width="600">\n'
                '<tr><td><img src="https://example.com/hero.png" alt="Hero image" '
                'width="600" height="300"></td></tr>\n'
                '<tr><td><a href="https://example.com">Visit us</a></td></tr>\n'
                "</table>\n</body>\n</html>\n"
                "```"
            ),
            model="test-model",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
        )

    @pytest.mark.asyncio()
    async def test_happy_path_with_maizzle_unavailable(
        self, valid_html_response: CompletionResponse
    ) -> None:
        """Full pipeline where scaffolder generates valid HTML but Maizzle is unavailable.

        Expected path: scaffolder → qa_gate(pass) → maizzle_build(fail due to no sidecar)
        """
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = valid_html_response

        definition = build_campaign_blueprint()

        with (
            patch("app.ai.blueprints.nodes.scaffolder_node.get_registry") as mock_registry,
            patch("app.ai.blueprints.nodes.scaffolder_node.get_settings") as mock_settings,
            patch(
                "app.ai.blueprints.nodes.scaffolder_node.resolve_model",
                return_value="complex-model",
            ),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_settings.return_value.maizzle_builder_url = "http://localhost:3001"
            mock_registry.return_value.get_llm.return_value = mock_provider

            engine = BlueprintEngine(definition)
            run = await engine.run(brief="Create a Black Friday promo email")

        # Scaffolder should have been called
        assert mock_provider.complete.call_count >= 1

        # Check progress log
        node_names = [p.node_name for p in run.progress]
        assert node_names[0] == "scaffolder"
        assert "qa_gate" in node_names

        # Verify model usage was tracked
        assert run.model_usage["total_tokens"] > 0

    @pytest.mark.asyncio()
    async def test_node_execution_order_in_progress(
        self, valid_html_response: CompletionResponse
    ) -> None:
        """Verify the progress log captures node execution order."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = valid_html_response

        definition = build_campaign_blueprint()

        with (
            patch("app.ai.blueprints.nodes.scaffolder_node.get_registry") as mock_registry,
            patch("app.ai.blueprints.nodes.scaffolder_node.get_settings") as mock_settings,
            patch(
                "app.ai.blueprints.nodes.scaffolder_node.resolve_model",
                return_value="complex-model",
            ),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_settings.return_value.maizzle_builder_url = "http://localhost:3001"
            mock_registry.return_value.get_llm.return_value = mock_provider

            engine = BlueprintEngine(definition)
            run = await engine.run(brief="Create a newsletter")

        # First node is always scaffolder
        assert run.progress[0].node_name == "scaffolder"
        assert run.progress[0].node_type == "agentic"

        # All progress entries have required fields
        for entry in run.progress:
            assert entry.node_name
            assert entry.node_type in ("deterministic", "agentic")
            assert entry.status in ("success", "failed", "skipped")
            assert entry.duration_ms >= 0

    @pytest.mark.asyncio()
    async def test_campaign_blueprint_structure(self) -> None:
        """Verify the campaign blueprint has correct graph structure."""
        definition = build_campaign_blueprint()

        assert definition.name == "campaign"
        assert definition.entry_node == "scaffolder"
        assert "scaffolder" in definition.nodes
        assert "qa_gate" in definition.nodes
        assert "maizzle_build" in definition.nodes
        assert "export" in definition.nodes
        assert "recovery_router" in definition.nodes
        assert "dark_mode" in definition.nodes
        assert "outlook_fixer" in definition.nodes
        assert "accessibility" in definition.nodes
        assert "personalisation" in definition.nodes
        assert "code_reviewer" in definition.nodes
        assert "knowledge" in definition.nodes
        assert "innovation" in definition.nodes

        # Verify edge count (13 + 2 for code_reviewer route + loop)
        assert len(definition.edges) == 15

        # Verify agentic vs deterministic
        assert definition.nodes["scaffolder"].node_type == "agentic"
        assert definition.nodes["dark_mode"].node_type == "agentic"
        assert definition.nodes["outlook_fixer"].node_type == "agentic"
        assert definition.nodes["accessibility"].node_type == "agentic"
        assert definition.nodes["personalisation"].node_type == "agentic"
        assert definition.nodes["code_reviewer"].node_type == "agentic"
        assert definition.nodes["knowledge"].node_type == "agentic"
        assert definition.nodes["innovation"].node_type == "agentic"
        assert definition.nodes["qa_gate"].node_type == "deterministic"
        assert definition.nodes["maizzle_build"].node_type == "deterministic"
        assert definition.nodes["export"].node_type == "deterministic"
        assert definition.nodes["recovery_router"].node_type == "deterministic"
