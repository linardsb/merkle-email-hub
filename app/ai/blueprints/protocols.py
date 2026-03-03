"""Core types and protocols for the Blueprint state machine engine.

Defines the contract that all blueprint nodes must satisfy, along with
the context and result data structures that flow through the graph.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

NodeType = Literal["deterministic", "agentic"]
NodeStatus = Literal["success", "failed", "skipped"]


@dataclass
class NodeContext:
    """Scoped context passed to each node during execution.

    Implements progressive context hydration — each node receives only
    the data relevant to its task, avoiding "lost in the middle" issues.

    Attributes:
        html: Current HTML state flowing through the pipeline.
        brief: Original campaign brief (for agentic nodes).
        node_rules: Node-specific system prompt or instructions.
        qa_failures: Failed QA check details from previous iteration.
        iteration: Current self-correction iteration (0-based).
        metadata: Arbitrary key-value metadata for extensibility.
    """

    html: str = ""
    brief: str = ""
    node_rules: str = ""
    qa_failures: list[str] = field(default_factory=lambda: list[str]())
    iteration: int = 0
    metadata: dict[str, object] = field(default_factory=lambda: dict[str, object]())


@dataclass
class NodeResult:
    """Output from a blueprint node execution.

    Attributes:
        status: Whether the node succeeded, failed, or was skipped.
        html: Transformed HTML output (may be unchanged for analysis nodes).
        details: Human-readable summary of what the node did.
        error: Error message if the node failed.
        usage: Token usage stats for agentic nodes (None for deterministic).
    """

    status: NodeStatus
    html: str = ""
    details: str = ""
    error: str = ""
    usage: dict[str, int] | None = None


@runtime_checkable
class BlueprintNode(Protocol):
    """Protocol that all blueprint nodes must satisfy.

    Nodes are either deterministic (no LLM calls) or agentic (LLM-powered).
    The engine calls execute() and routes based on the result status.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this node within a blueprint."""
        ...

    @property
    def node_type(self) -> NodeType:
        """Whether this node is deterministic or agentic."""
        ...

    async def execute(self, context: NodeContext) -> NodeResult:
        """Execute this node with the given context.

        Args:
            context: Scoped context for this node's execution.

        Returns:
            NodeResult with status, transformed HTML, and metadata.
        """
        ...
