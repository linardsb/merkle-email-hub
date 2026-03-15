"""Tests for design system injection into blueprint engine context."""

from __future__ import annotations

import pytest

from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.projects.design_system import BrandPalette, DesignSystem


class StubAgenticNode:
    """Agentic node that captures context for test assertions."""

    def __init__(self, name: str = "test_agentic") -> None:
        self._name = name
        self.captured_context: NodeContext | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        self.captured_context = context
        return NodeResult(status="success", html="<p>done</p>")


class StubDeterministicNode:
    """Deterministic node that captures context for test assertions."""

    def __init__(self, name: str = "test_deterministic") -> None:
        self._name = name
        self.captured_context: NodeContext | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        self.captured_context = context
        return NodeResult(status="success", html="<p>done</p>")


def _make_ds() -> DesignSystem:
    return DesignSystem(
        palette=BrandPalette(
            primary="#ff0000",
            secondary="#00ff00",
            accent="#0000ff",
        ),
    )


class TestDesignSystemInjection:
    @pytest.mark.anyio
    async def test_agentic_node_receives_design_system(self) -> None:
        node = StubAgenticNode()
        definition = BlueprintDefinition(
            name="test",
            nodes={"test_agentic": node},
            edges=[],
            entry_node="test_agentic",
        )
        ds = _make_ds()
        engine = BlueprintEngine(definition, design_system=ds)
        await engine.run("test brief")

        assert node.captured_context is not None
        assert node.captured_context.metadata["design_system"] is ds
        assert "ds_color_map" in node.captured_context.metadata
        assert "ds_font_map" in node.captured_context.metadata
        color_map = node.captured_context.metadata["ds_color_map"]
        assert isinstance(color_map, dict)
        assert color_map["primary"] == "#ff0000"

    @pytest.mark.anyio
    async def test_no_design_system_no_metadata(self) -> None:
        node = StubAgenticNode()
        definition = BlueprintDefinition(
            name="test",
            nodes={"test_agentic": node},
            edges=[],
            entry_node="test_agentic",
        )
        engine = BlueprintEngine(definition)
        await engine.run("test brief")

        assert node.captured_context is not None
        assert "design_system" not in node.captured_context.metadata
        assert "ds_color_map" not in node.captured_context.metadata

    @pytest.mark.anyio
    async def test_deterministic_node_receives_design_system(self) -> None:
        """Deterministic nodes also receive design system (for brand repair)."""
        node = StubDeterministicNode()
        definition = BlueprintDefinition(
            name="test",
            nodes={"test_deterministic": node},
            edges=[],
            entry_node="test_deterministic",
        )
        ds = _make_ds()
        engine = BlueprintEngine(definition, design_system=ds)
        await engine.run("test brief")

        assert node.captured_context is not None
        assert node.captured_context.metadata["design_system"] is ds
        assert "ds_color_map" in node.captured_context.metadata

    @pytest.mark.anyio
    async def test_multiple_agentic_nodes_all_receive(self) -> None:
        node1 = StubAgenticNode("scaffolder")
        node2 = StubAgenticNode("dark_mode")
        definition = BlueprintDefinition(
            name="test",
            nodes={"scaffolder": node1, "dark_mode": node2},
            edges=[Edge(from_node="scaffolder", to_node="dark_mode", condition="success")],
            entry_node="scaffolder",
        )
        ds = _make_ds()
        engine = BlueprintEngine(definition, design_system=ds)
        await engine.run("test brief")

        assert node1.captured_context is not None
        assert node1.captured_context.metadata["design_system"] is ds
        assert node2.captured_context is not None
        assert node2.captured_context.metadata["design_system"] is ds
