"""Tests for pipeline DAG schema and topological sorting."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.ai.pipeline.dag import PipelineDag, PipelineNode
from app.ai.pipeline.registry import get_pipeline_registry
from app.core.exceptions import CyclicDependencyError


class TestTopologicalSort:
    """Kahn's algorithm and level grouping."""

    def test_three_level_topology(self, three_level_dag: PipelineDag) -> None:
        levels = three_level_dag.topological_levels()
        assert levels == [["a"], ["b", "c"], ["d"]]

    def test_single_node(self) -> None:
        dag = PipelineDag(
            name="single",
            description="",
            nodes={"x": PipelineNode("agent_x", "standard", inputs=(), outputs=("out",))},
        )
        assert dag.topological_levels() == [["x"]]

    def test_all_independent(self) -> None:
        nodes = {
            "x": PipelineNode("a1", "standard", inputs=(), outputs=("o1",)),
            "y": PipelineNode("a2", "standard", inputs=(), outputs=("o2",)),
            "z": PipelineNode("a3", "standard", inputs=(), outputs=("o3",)),
        }
        dag = PipelineDag(name="flat", description="", nodes=nodes)
        levels = dag.topological_levels()
        assert len(levels) == 1
        assert sorted(levels[0]) == ["x", "y", "z"]

    def test_linear_chain(self) -> None:
        nodes = {
            "a": PipelineNode("a1", "complex", inputs=(), outputs=("x",)),
            "b": PipelineNode("a2", "standard", inputs=("x",), outputs=("y",)),
            "c": PipelineNode("a3", "lightweight", inputs=("y",), outputs=("z",)),
        }
        dag = PipelineDag(name="chain", description="", nodes=nodes)
        assert dag.topological_levels() == [["a"], ["b"], ["c"]]

    def test_cyclic_raises(self) -> None:
        nodes = {
            "a": PipelineNode("a1", "standard", inputs=("y",), outputs=("x",)),
            "b": PipelineNode("a2", "standard", inputs=("x",), outputs=("y",)),
        }
        with pytest.raises(CyclicDependencyError) as exc_info:
            PipelineDag(name="cycle", description="", nodes=nodes)
        assert len(exc_info.value.cycle) > 0

    def test_self_loop_excluded(self) -> None:
        """A node that produces and consumes the same artifact is NOT a self-loop."""
        nodes = {
            "a": PipelineNode("a1", "standard", inputs=("html",), outputs=("html",)),
        }
        dag = PipelineDag(name="self", description="", nodes=nodes)
        assert dag.topological_levels() == [["a"]]

    def test_deterministic_level_order(self, three_level_nodes: dict[str, PipelineNode]) -> None:
        dag1 = PipelineDag(name="d1", description="", nodes=three_level_nodes)
        dag2 = PipelineDag(name="d2", description="", nodes=three_level_nodes)
        assert dag1.topological_levels() == dag2.topological_levels()


class TestFrozenDataclasses:
    """Immutability checks."""

    def test_frozen_node(self) -> None:
        node = PipelineNode("a", "standard", inputs=(), outputs=())
        with pytest.raises(FrozenInstanceError):
            node.agent_name = "b"  # type: ignore[misc]

    def test_frozen_dag(self, three_level_dag: PipelineDag) -> None:
        with pytest.raises(FrozenInstanceError):
            three_level_dag.name = "changed"  # type: ignore[misc]


class TestValidation:
    """DAG artifact wiring and agent name validation."""

    def test_validate_missing_input(self) -> None:
        nodes = {
            "a": PipelineNode("a1", "standard", inputs=("missing_artifact",), outputs=("x",)),
        }
        dag = PipelineDag(name="missing", description="", nodes=nodes)
        warnings = dag.validate()
        assert any("missing_artifact" in w for w in warnings)

    def test_validate_all_wired(self, three_level_dag: PipelineDag) -> None:
        warnings = three_level_dag.validate()
        assert warnings == []

    def test_validate_unknown_agent(self, three_level_dag: PipelineDag) -> None:
        warnings = three_level_dag.validate(known_agents=["agent_a", "agent_b"])
        assert any("agent_c" in w for w in warnings)
        assert any("agent_d" in w for w in warnings)

    def test_validate_no_known_agents(self, three_level_dag: PipelineDag) -> None:
        warnings = three_level_dag.validate(known_agents=None)
        assert warnings == []

    def test_full_build_template_levels(self) -> None:
        registry = get_pipeline_registry()
        dag = registry.get("full-build")
        levels = dag.topological_levels()
        assert len(levels) == 2
        assert levels[0] == ["scaffolder"]
        # All other agents depend only on scaffolder's html — same level
        rest = sorted(levels[1])
        assert rest == [
            "accessibility",
            "code_reviewer",
            "content",
            "dark_mode",
            "personalisation",
            "visual_qa",
        ]
