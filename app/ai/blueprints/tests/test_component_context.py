# pyright: reportReturnType=false, reportArgumentType=false
"""Tests for component reference detection and context formatting."""

import pytest

from app.ai.blueprints.component_context import detect_component_refs, format_component_context
from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
from app.ai.blueprints.protocols import ComponentMeta, NodeContext, NodeResult, NodeType


class TestDetectComponentRefs:
    """Tests for Maizzle <component> tag detection."""

    def test_detect_single_ref(self) -> None:
        html = '<component src="components/header.html" />'
        assert detect_component_refs(html) == ["header"]

    def test_detect_multiple_refs(self) -> None:
        html = """
        <component src="components/header.html" />
        <component src="components/cta-button.html" />
        <component src="components/footer.html" />
        """
        assert detect_component_refs(html) == ["header", "cta-button", "footer"]

    def test_detect_without_extension(self) -> None:
        html = '<component src="components/hero" />'
        assert detect_component_refs(html) == ["hero"]

    def test_deduplicate_refs(self) -> None:
        html = """
        <component src="components/header.html" />
        <component src="components/header.html" />
        """
        assert detect_component_refs(html) == ["header"]

    def test_no_refs_in_plain_html(self) -> None:
        html = "<table><tr><td>Hello</td></tr></table>"
        assert detect_component_refs(html) == []

    def test_case_insensitive(self) -> None:
        html = '<COMPONENT src="components/header.html" />'
        assert detect_component_refs(html) == ["header"]


class TestFormatComponentContext:
    """Tests for formatting ComponentMeta into agent-readable context."""

    def test_format_single_component(self) -> None:
        meta = ComponentMeta(
            slug="header",
            name="Email Header",
            category="layout",
            description="Responsive email header with logo",
            compatibility={"outlook": "full", "gmail": "partial"},
            html_snippet="<table><tr><td>Header</td></tr></table>",
        )
        result = format_component_context([meta])
        assert "--- COMPONENT CONTEXT ---" in result
        assert "Email Header (header) [layout]" in result
        assert "Responsive email header" in result
        assert "outlook: full" in result
        assert "HTML preview:" in result

    def test_format_empty_list(self) -> None:
        assert format_component_context([]) == ""

    def test_format_minimal_component(self) -> None:
        meta = ComponentMeta(
            slug="btn",
            name="Button",
            category="interactive",
            description="",
            compatibility={},
            html_snippet="",
        )
        result = format_component_context([meta])
        assert "Button (btn) [interactive]" in result
        assert "Compatibility" not in result
        assert "HTML preview" not in result


class TestComponentContextInjection:
    """Tests for component context being injected into engine node context."""

    @pytest.mark.asyncio()
    async def test_resolver_none_no_error(self) -> None:
        """Engine with no resolver runs fine (backward compat)."""

        class SimpleNode:
            @property
            def name(self) -> str:
                return "node"

            @property
            def node_type(self) -> NodeType:
                return "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                return NodeResult(status="success", html="<p>ok</p>")

        definition = BlueprintDefinition(
            name="no-resolver",
            nodes={"node": SimpleNode()},
            edges=[],
            entry_node="node",
        )

        engine = BlueprintEngine(definition, component_resolver=None)
        run = await engine.run(brief="test")
        assert run.status == "completed"

    @pytest.mark.asyncio()
    async def test_component_context_injected_for_agentic_nodes(self) -> None:
        """Mock resolver provides component metadata that appears in context."""
        captured_contexts: list[NodeContext] = []

        class CapturingNode:
            @property
            def name(self) -> str:
                return "agent"

            @property
            def node_type(self) -> NodeType:
                return "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                captured_contexts.append(context)
                return NodeResult(status="success", html="<p>done</p>")

        class MockResolver:
            async def resolve(self, slugs: list[str]) -> list[ComponentMeta]:
                return [
                    ComponentMeta(
                        slug=s,
                        name=f"Component {s}",
                        category="layout",
                        description=f"A {s} component",
                        compatibility={"outlook": "full"},
                        html_snippet="<table></table>",
                    )
                    for s in slugs
                ]

        # First node produces HTML with component refs
        class ProducerNode:
            @property
            def name(self) -> str:
                return "producer"

            @property
            def node_type(self) -> NodeType:
                return "deterministic"

            async def execute(self, context: NodeContext) -> NodeResult:
                return NodeResult(
                    status="success",
                    html='<component src="components/header.html" /><component src="components/footer.html" />',
                )

        definition = BlueprintDefinition(
            name="inject-test",
            nodes={"producer": ProducerNode(), "agent": CapturingNode()},
            edges=[Edge(from_node="producer", to_node="agent", condition="always")],
            entry_node="producer",
        )

        engine = BlueprintEngine(definition, component_resolver=MockResolver())
        await engine.run(brief="test")

        assert len(captured_contexts) == 1
        ctx = captured_contexts[0]
        component_ctx = ctx.metadata.get("component_context", "")
        assert isinstance(component_ctx, str)
        assert "Component header" in component_ctx
        assert "Component footer" in component_ctx
        assert "outlook: full" in component_ctx

    @pytest.mark.asyncio()
    async def test_no_refs_no_resolver_call(self) -> None:
        """When HTML has no component refs, resolver is not called."""
        resolver_called = False

        class TrackingResolver:
            async def resolve(self, slugs: list[str]) -> list[ComponentMeta]:
                nonlocal resolver_called
                resolver_called = True
                return []

        class SimpleNode:
            @property
            def name(self) -> str:
                return "agent"

            @property
            def node_type(self) -> NodeType:
                return "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                return NodeResult(status="success", html="<p>plain</p>")

        # Need initial HTML without component refs
        class ProducerNode:
            @property
            def name(self) -> str:
                return "producer"

            @property
            def node_type(self) -> NodeType:
                return "deterministic"

            async def execute(self, context: NodeContext) -> NodeResult:
                return NodeResult(status="success", html="<table><tr><td>no refs</td></tr></table>")

        definition = BlueprintDefinition(
            name="no-refs",
            nodes={"producer": ProducerNode(), "agent": SimpleNode()},
            edges=[Edge(from_node="producer", to_node="agent", condition="always")],
            entry_node="producer",
        )

        engine = BlueprintEngine(definition, component_resolver=TrackingResolver())
        await engine.run(brief="test")

        assert not resolver_called
