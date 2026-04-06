"""Pipeline DAG schema with topological sorting and validation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.exceptions import CyclicDependencyError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = get_logger(__name__)


@dataclass(frozen=True)
class PipelineNode:
    """Single node in a pipeline DAG."""

    agent_name: str
    tier: str  # "complex" | "standard" | "lightweight" — matches TaskTier literal
    inputs: tuple[str, ...]  # artifact names consumed (e.g., "html", "qa_results")
    outputs: tuple[str, ...]  # artifact names produced
    contract: str | None = None  # post-condition name (e.g., "html_valid")


@dataclass(frozen=True)
class PipelineDag:
    """Directed acyclic graph of pipeline nodes.

    Validates acyclicity at construction via __post_init__.
    """

    name: str
    description: str
    nodes: dict[str, PipelineNode]  # node_id → PipelineNode
    _levels: tuple[tuple[str, ...], ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        levels = _topological_sort(self.nodes)
        object.__setattr__(self, "_levels", levels)

    def topological_levels(self) -> list[list[str]]:
        """Nodes grouped by execution level — same-level nodes can run in parallel."""
        return [list(level) for level in self._levels]

    def validate(self, known_agents: Sequence[str] | None = None) -> list[str]:
        """Check input/output artifact wiring and agent name validity.

        Returns list of warning strings (empty = valid).
        """
        warnings: list[str] = []
        # Collect all produced artifacts (node_id → set of artifact names)
        produced: dict[str, set[str]] = {}
        for node_id, node in self.nodes.items():
            produced[node_id] = set(node.outputs)

        # Build level index: node_id → level number
        level_of: dict[str, int] = {}
        for lvl_idx, lvl in enumerate(self._levels):
            for nid in lvl:
                level_of[nid] = lvl_idx

        # All artifacts available at each level (cumulative from prior levels)
        available_at: dict[int, set[str]] = {}
        for lvl_idx, lvl in enumerate(self._levels):
            prev = available_at.get(lvl_idx - 1, set())
            current = set(prev)
            for nid in lvl:
                current |= produced.get(nid, set())
            available_at[lvl_idx] = current

        # Check each node's inputs are available from prior levels
        for node_id, node in self.nodes.items():
            node_lvl = level_of[node_id]
            available = available_at.get(node_lvl - 1, set()) if node_lvl > 0 else set()
            for inp in node.inputs:
                if inp not in available:
                    warnings.append(
                        f"Node '{node_id}' requires input '{inp}' not produced by any upstream node"
                    )

        # Check agent names if registry provided
        if known_agents is not None:
            agent_set = set(known_agents)
            for node_id, node in self.nodes.items():
                if node.agent_name not in agent_set:
                    warnings.append(
                        f"Node '{node_id}' references unknown agent '{node.agent_name}'"
                    )

        return warnings


def _topological_sort(
    nodes: dict[str, PipelineNode],
) -> tuple[tuple[str, ...], ...]:
    """Kahn's algorithm — returns nodes grouped by level.

    Raises CyclicDependencyError if the graph has a cycle.
    """
    # Build adjacency from artifact dependencies:
    # node A → node B if B.inputs ∩ A.outputs ≠ ∅
    artifact_producers: dict[str, list[str]] = {}  # artifact → producer node_ids
    for node_id, node in nodes.items():
        for out in node.outputs:
            artifact_producers.setdefault(out, []).append(node_id)

    # in-degree per node, edges: producer → consumer
    in_degree: dict[str, int] = dict.fromkeys(nodes, 0)
    edges: dict[str, set[str]] = {nid: set() for nid in nodes}

    for node_id, node in nodes.items():
        seen_producers: set[str] = set()
        for inp in node.inputs:
            for producer in artifact_producers.get(inp, []):
                if producer != node_id and producer not in seen_producers:
                    seen_producers.add(producer)
                    edges[producer].add(node_id)
                    in_degree[node_id] += 1

    # Kahn's
    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    levels: list[tuple[str, ...]] = []
    processed = 0

    while queue:
        level = tuple(sorted(queue))  # sorted for determinism
        levels.append(level)
        next_queue: deque[str] = deque()
        for nid in level:
            processed += 1
            for downstream in sorted(edges[nid]):
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    next_queue.append(downstream)
        queue = next_queue

    if processed != len(nodes):
        # Find nodes in cycle for error message
        remaining = [nid for nid in nodes if in_degree[nid] > 0]
        raise CyclicDependencyError(cycle=remaining)

    return tuple(levels)
