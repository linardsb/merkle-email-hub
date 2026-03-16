"""Tests for individual blueprint node implementations."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.blueprints.nodes.export_node import ExportNode
from app.ai.blueprints.nodes.qa_gate_node import QAGateNode
from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
from app.ai.blueprints.nodes.scaffolder_node import ScaffolderNode
from app.ai.blueprints.protocols import NodeContext


class TestQAGateNode:
    """Tests for the deterministic QA gate node."""

    @pytest.mark.asyncio()
    async def test_passes_with_valid_html(self, sample_html_valid: str) -> None:
        node = QAGateNode()
        context = NodeContext(html=sample_html_valid)
        result = await node.execute(context)

        assert result.status == "success"
        assert "passed" in result.details.lower()

    @pytest.mark.asyncio()
    async def test_fails_with_minimal_html(self, sample_html_minimal: str) -> None:
        node = QAGateNode()
        context = NodeContext(html=sample_html_minimal)
        result = await node.execute(context)

        assert result.status == "failed"
        assert result.details  # should contain failure descriptions

    @pytest.mark.asyncio()
    async def test_fails_with_no_html(self) -> None:
        node = QAGateNode()
        context = NodeContext(html="")
        result = await node.execute(context)

        assert result.status == "failed"
        assert "No HTML" in result.error

    @pytest.mark.asyncio()
    async def test_preserves_html_in_result(self, sample_html_valid: str) -> None:
        node = QAGateNode()
        context = NodeContext(html=sample_html_valid)
        result = await node.execute(context)

        assert result.html == sample_html_valid

    @pytest.mark.asyncio()
    async def test_node_metadata(self) -> None:
        node = QAGateNode()
        assert node.name == "qa_gate"
        assert node.node_type == "deterministic"


class TestRecoveryRouterNode:
    """Tests for the deterministic recovery router node."""

    @pytest.mark.asyncio()
    async def test_routes_dark_mode_to_dark_mode_node(self) -> None:
        node = RecoveryRouterNode()
        context = NodeContext(
            html="<p>test</p>",
            qa_failures=["dark_mode: missing color-scheme meta"],
        )
        result = await node.execute(context)

        assert result.status == "success"
        assert "route_to:dark_mode" in result.details

    @pytest.mark.asyncio()
    async def test_routes_accessibility_failures_to_accessibility(self) -> None:
        node = RecoveryRouterNode()
        context = NodeContext(
            html="<p>test</p>",
            qa_failures=["accessibility: no lang", "accessibility: missing alt text"],
        )
        result = await node.execute(context)

        assert result.status == "success"
        assert "route_to:accessibility" in result.details

    @pytest.mark.asyncio()
    async def test_routes_other_failures_to_scaffolder(self) -> None:
        node = RecoveryRouterNode()
        context = NodeContext(
            html="<p>test</p>",
            qa_failures=["html_validation: missing DOCTYPE", "link_validation: broken links"],
        )
        result = await node.execute(context)

        assert result.status == "success"
        assert "route_to:scaffolder" in result.details

    @pytest.mark.asyncio()
    async def test_defaults_to_scaffolder_with_no_failures(self) -> None:
        node = RecoveryRouterNode()
        context = NodeContext(html="<p>test</p>", qa_failures=[])
        result = await node.execute(context)

        assert "route_to:scaffolder" in result.details

    @pytest.mark.asyncio()
    async def test_preserves_html(self) -> None:
        node = RecoveryRouterNode()
        html = "<p>preserved</p>"
        context = NodeContext(html=html, qa_failures=["dark_mode: fail"])
        result = await node.execute(context)

        assert result.html == html

    @pytest.mark.asyncio()
    async def test_node_metadata(self) -> None:
        node = RecoveryRouterNode()
        assert node.name == "recovery_router"
        assert node.node_type == "deterministic"


class TestExportNode:
    """Tests for the deterministic export node."""

    @pytest.mark.asyncio()
    async def test_passes_through_raw_html(self) -> None:
        node = ExportNode()
        context = NodeContext(html="<p>email content</p>")
        result = await node.execute(context)

        assert result.status == "success"
        assert result.html == "<p>email content</p>"

    @pytest.mark.asyncio()
    async def test_fails_with_no_html(self) -> None:
        node = ExportNode()
        context = NodeContext(html="")
        result = await node.execute(context)

        assert result.status == "failed"
        assert "No HTML" in result.error

    @pytest.mark.asyncio()
    async def test_node_metadata(self) -> None:
        node = ExportNode()
        assert node.name == "export"
        assert node.node_type == "deterministic"


class TestScaffolderNode:
    """Tests for the agentic scaffolder node."""

    @pytest.mark.asyncio()
    async def test_generates_html_with_mocked_llm(self, mock_provider: AsyncMock) -> None:
        node = ScaffolderNode()
        context = NodeContext(brief="Create a welcome email")

        with (
            patch("app.ai.blueprints.nodes.scaffolder_node.get_registry") as mock_registry,
            patch("app.ai.blueprints.nodes.scaffolder_node.get_settings") as mock_settings,
            patch(
                "app.ai.blueprints.nodes.scaffolder_node.resolve_model",
                return_value="complex-model",
            ),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            result = await node.execute(context)

        assert result.status == "success"
        assert result.html  # should have extracted HTML
        assert result.usage is not None
        assert result.usage["total_tokens"] == 300

    @pytest.mark.asyncio()
    async def test_retry_injects_qa_failures(self, mock_provider: AsyncMock) -> None:
        node = ScaffolderNode()
        context = NodeContext(
            brief="Create a welcome email",
            qa_failures=["dark_mode: missing meta", "accessibility: no lang"],
            iteration=1,
            metadata={"progress_anchor": "[PROGRESS] scaffolder:ok → qa_gate:2_failed"},
        )

        with (
            patch("app.ai.blueprints.nodes.scaffolder_node.get_registry") as mock_registry,
            patch("app.ai.blueprints.nodes.scaffolder_node.get_settings") as mock_settings,
            patch(
                "app.ai.blueprints.nodes.scaffolder_node.resolve_model",
                return_value="complex-model",
            ),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            await node.execute(context)

        # Verify QA failures were injected into the user message
        call_args = mock_provider.complete.call_args
        user_msg = call_args[0][0][1].content
        assert "QA FAILURES" in user_msg
        assert "dark_mode" in user_msg
        assert "PROGRESS" in user_msg

    @pytest.mark.asyncio()
    async def test_llm_failure_returns_failed_result(self) -> None:
        failing_provider = AsyncMock()
        failing_provider.complete.side_effect = RuntimeError("LLM down")

        node = ScaffolderNode()
        context = NodeContext(brief="Create an email")

        with (
            patch("app.ai.blueprints.nodes.scaffolder_node.get_registry") as mock_registry,
            patch("app.ai.blueprints.nodes.scaffolder_node.get_settings") as mock_settings,
            patch(
                "app.ai.blueprints.nodes.scaffolder_node.resolve_model",
                return_value="complex-model",
            ),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = failing_provider

            result = await node.execute(context)

        assert result.status == "failed"
        assert "LLM call failed" in result.error

    @pytest.mark.asyncio()
    async def test_node_metadata(self) -> None:
        node = ScaffolderNode()
        assert node.name == "scaffolder"
        assert node.node_type == "agentic"
