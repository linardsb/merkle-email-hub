"""Core types and protocols for the Blueprint state machine engine.

Defines the contract that all blueprint nodes must satisfy, along with
the context and result data structures that flow through the graph.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.ai.agents.schemas.build_plan import EmailBuildPlan
    from app.ai.multimodal import ContentBlock
    from app.knowledge.graph.protocols import GraphSearchResult

__all__ = [
    "AgentHandoff",
    "AllowedScope",
    "BlueprintNode",
    "ComponentMeta",
    "ComponentResolver",
    "GraphContextProvider",
    "HandoffStatus",
    "NodeContext",
    "NodeResult",
    "NodeStatus",
    "NodeType",
    "StructuredFailure",
]

NodeType = Literal["deterministic", "agentic"]
NodeStatus = Literal["success", "failed", "skipped"]


class HandoffStatus(StrEnum):
    """Status of an agentic node's execution for orchestrator routing."""

    OK = "ok"
    WARNING = "warning"  # completed but with concerns
    BLOCKED = "blocked"  # cannot proceed (missing dependency)
    FAILED = "failed"  # execution error


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
    build_plan: EmailBuildPlan | None = None
    multimodal_context: list[ContentBlock] | None = None

    def merge_metadata(self, updates: Mapping[str, object]) -> None:
        """Merge layer output into metadata; last-write-wins per key."""
        self.metadata.update(updates)


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
    handoff: AgentHandoff | None = None
    structured_failures: tuple[StructuredFailure, ...] = ()


@dataclass(frozen=True)
class AgentHandoff:
    """Structured output from an agentic blueprint node.

    Carries metadata about agent decisions, warnings, component references,
    and self-assessed confidence to downstream nodes.
    """

    status: HandoffStatus = HandoffStatus.OK
    agent_name: str = ""
    artifact: str = ""
    decisions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    component_refs: tuple[str, ...] = ()
    confidence: float | None = None
    uncertainties: tuple[str, ...] = ()
    typed_payload: object | None = None  # HandoffPayload at runtime, object for protocol decoupling
    learnings: tuple[str, ...] = ()  # What the agent learned during this execution

    def compact(self) -> AgentHandoff:
        """Return a copy with large fields stripped (artifact cleared)."""
        return AgentHandoff(
            status=self.status,
            agent_name=self.agent_name,
            artifact="",
            decisions=self.decisions,
            warnings=self.warnings,
            component_refs=self.component_refs,
            confidence=self.confidence,
            uncertainties=self.uncertainties,
            typed_payload=self.typed_payload,
            learnings=self.learnings,
        )

    def summary(self) -> str:
        """Return a single-line summary string for decayed handoff history."""
        conf = f" conf={self.confidence:.2f}" if self.confidence is not None else ""
        unc = f" unc={len(self.uncertainties)}" if self.uncertainties else ""
        lrn = f" lrn={len(self.learnings)}" if self.learnings else ""
        return f"{self.agent_name}: {self.status.value}{conf}{unc}{lrn}"


@dataclass(frozen=True)
class StructuredFailure:
    """Structured QA failure with routing metadata."""

    check_name: str
    score: float
    details: str
    suggested_agent: str
    priority: int  # lower = higher priority (1 = highest)
    severity: str = "warning"

    def compact(self) -> StructuredFailure:
        """Return a copy with large fields stripped (details cleared)."""
        return StructuredFailure(
            check_name=self.check_name,
            score=self.score,
            details="",
            suggested_agent=self.suggested_agent,
            priority=self.priority,
            severity=self.severity,
        )


@dataclass(frozen=True)
class AllowedScope:
    """Defines what a fixer agent is allowed to modify on retry.

    Used by scope_validator to reject changes outside the agent's domain.
    """

    styles_only: bool = False
    additive_only: bool = False
    text_only: bool = False
    structure_only: bool = False


@dataclass(frozen=True)
class ComponentMeta:
    """Lightweight component metadata for agent context injection."""

    slug: str
    name: str
    category: str
    description: str
    compatibility: dict[str, str]
    html_snippet: str


class ComponentResolver(Protocol):
    """Protocol for resolving component slugs to metadata."""

    async def resolve(self, slugs: list[str]) -> list[ComponentMeta]: ...


@runtime_checkable
class GraphContextProvider(Protocol):
    """Protocol for graph-backed context retrieval in blueprint nodes."""

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[GraphSearchResult]: ...

    async def search_completion(
        self,
        query: str,
        *,
        system_prompt: str = "",
    ) -> str: ...


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
