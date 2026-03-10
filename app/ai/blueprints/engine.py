"""Blueprint state machine engine — routes between deterministic and agentic nodes."""

import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from app.ai.blueprints.audience_context import AudienceProfile
    from app.knowledge.graph.protocols import GraphSearchResult

from app.ai.blueprints.exceptions import BlueprintEscalatedError, BlueprintNodeError
from app.ai.blueprints.protocols import (
    AgentHandoff,
    BlueprintNode,
    ComponentResolver,
    GraphContextProvider,
    HandoffStatus,
    NodeContext,
    NodeResult,
)
from app.ai.blueprints.route_advisor import is_node_relevant
from app.ai.blueprints.schemas import BlueprintProgress
from app.core.logging import get_logger

logger = get_logger(__name__)

# Callback type for persisting handoffs to memory after each agentic node.
# Signature: (handoff, run_id, project_id) -> None
HandoffMemoryCallback = Callable[[AgentHandoff, str, int | None], Coroutine[Any, Any, None]]

# Callback type for logging completed run outcomes to graph + memory.
# Signature: (run, blueprint_name, project_id) -> None
OutcomeCallback = Callable[["BlueprintRun", str, int | None], Coroutine[Any, Any, None]]

MAX_SELF_CORRECTION_ROUNDS = 2
MAX_TOTAL_STEPS = 20  # safety brake
CONFIDENCE_REVIEW_THRESHOLD = 0.5

EdgeCondition = Literal["success", "qa_fail", "always", "route_to"]


@dataclass
class Edge:
    """Directed edge between two blueprint nodes."""

    from_node: str
    to_node: str
    condition: EdgeCondition
    route_value: str = ""  # used when condition == "route_to"


@dataclass
class BlueprintDefinition:
    """Named graph of nodes and edges with an entry point."""

    name: str
    nodes: dict[str, BlueprintNode]
    edges: list[Edge]
    entry_node: str


@dataclass
class BlueprintRun:
    """Mutable state for a single blueprint execution."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "running"
    html: str = ""
    progress: list[BlueprintProgress] = field(default_factory=lambda: list[BlueprintProgress]())
    iteration_counts: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    qa_failures: list[str] = field(default_factory=lambda: list[str]())
    qa_passed: bool | None = None
    model_usage: dict[str, int] = field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )
    skipped_nodes: list[str] = field(default_factory=list)
    _last_result: NodeResult | None = field(default=None, repr=False)
    _last_handoff: AgentHandoff | None = field(default=None, repr=False)
    _handoff_history: list[AgentHandoff] = field(default_factory=list, repr=False)


class BlueprintEngine:
    """Executes a blueprint definition as a state machine.

    Interleaves deterministic nodes (QA gate, build, export) with
    agentic nodes (scaffolder, dark mode), supporting bounded
    self-correction via recovery routing.
    """

    def __init__(
        self,
        definition: BlueprintDefinition,
        component_resolver: ComponentResolver | None = None,
        on_handoff: HandoffMemoryCallback | None = None,
        project_id: int | None = None,
        graph_provider: GraphContextProvider | None = None,
        audience_profile: "AudienceProfile | None" = None,
    ) -> None:
        self._definition = definition
        self._component_resolver = component_resolver
        self._on_handoff = on_handoff
        self._project_id = project_id
        self._graph_provider = graph_provider
        self._audience_profile = audience_profile

    async def run(
        self, brief: str, initial_html: str = "", user_id: int | None = None
    ) -> BlueprintRun:
        """Execute the blueprint graph from entry to terminal node."""
        from app.core.quota import BlueprintCostTracker

        run = BlueprintRun(html=initial_html)
        current_node_name: str | None = self._definition.entry_node
        steps = 0

        # Set up cost tracking if user_id provided
        cost_tracker: BlueprintCostTracker | None = None
        if user_id is not None:
            from app.core.config import get_settings as _get_settings

            _settings = _get_settings()
            cost_tracker = BlueprintCostTracker(daily_cap=_settings.blueprint.daily_token_cap)

        logger.info(
            "blueprint.run_started",
            blueprint=self._definition.name,
            run_id=run.run_id,
        )

        while current_node_name is not None and steps < MAX_TOTAL_STEPS:
            steps += 1
            node = self._definition.nodes[current_node_name]

            # Track iteration count for agentic nodes
            iteration = run.iteration_counts.get(current_node_name, 0)
            if node.node_type == "agentic" and iteration >= MAX_SELF_CORRECTION_ROUNDS:
                raise BlueprintEscalatedError(current_node_name, iteration)

            # Skip irrelevant agentic nodes based on audience profile
            if node.node_type == "agentic" and not is_node_relevant(
                current_node_name, self._audience_profile
            ):
                logger.info(
                    "blueprint.node_skipped",
                    node=current_node_name,
                    run_id=run.run_id,
                    reason="audience_irrelevant",
                )
                run.skipped_nodes.append(current_node_name)
                run.progress.append(
                    BlueprintProgress(
                        node_name=current_node_name,
                        node_type=node.node_type,
                        status="skipped",
                        iteration=iteration,
                        summary="Skipped: not relevant for target audience",
                        duration_ms=0.0,
                    )
                )
                skip_result = NodeResult(status="skipped", html=run.html)
                current_node_name = self._resolve_next_node(current_node_name, skip_result)
                continue

            context = await self._build_node_context(node, run, brief, iteration)

            start = time.monotonic()
            try:
                result = await node.execute(context)
            except Exception as exc:
                logger.error(
                    "blueprints.node_failed",
                    node=current_node_name,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise BlueprintNodeError(current_node_name, "execution failed") from exc
            duration_ms = (time.monotonic() - start) * 1000

            # Record progress
            run.progress.append(
                BlueprintProgress(
                    node_name=current_node_name,
                    node_type=node.node_type,
                    status=result.status,
                    iteration=iteration,
                    summary=result.details or result.error or f"{result.status}",
                    duration_ms=round(duration_ms, 1),
                )
            )

            # Update run state
            if result.html:
                run.html = result.html
            if result.usage:
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    run.model_usage[key] += result.usage.get(key, 0)

            # Check token cost cap per node completion
            if cost_tracker is not None and user_id is not None and result.usage:
                node_tokens = result.usage.get("total_tokens", 0)
                if node_tokens > 0:
                    remaining = await cost_tracker.check_budget(user_id)
                    if remaining <= 0:
                        run.status = "cost_cap_exceeded"
                        logger.warning(
                            "blueprint.cost_cap_reached",
                            run_id=run.run_id,
                            user_id=user_id,
                            total_tokens=run.model_usage["total_tokens"],
                        )
                        break
                    await cost_tracker.record_usage(user_id, node_tokens)

            # Track QA results
            if current_node_name == "qa_gate":
                if result.status == "success":
                    run.qa_passed = True
                    run.qa_failures = []
                else:
                    run.qa_passed = False
                    run.qa_failures = [
                        line.strip() for line in result.details.split("\n") if line.strip()
                    ]

            # Increment iteration for agentic nodes
            if node.node_type == "agentic":
                run.iteration_counts[current_node_name] = iteration + 1

            run._last_result = result

            # Store handoff from agentic nodes
            if result.handoff is not None:
                run._last_handoff = result.handoff
                run._handoff_history.append(result.handoff)

                # Persist handoff as episodic memory (fire-and-forget)
                if self._on_handoff is not None:
                    try:
                        await self._on_handoff(result.handoff, run.run_id, self._project_id)
                    except Exception:
                        logger.warning(
                            "blueprint.handoff_memory_failed",
                            node=current_node_name,
                            run_id=run.run_id,
                            exc_info=True,
                        )

            # Low confidence → route to human review instead of retrying
            if (
                node.node_type == "agentic"
                and result.handoff is not None
                and result.handoff.confidence is not None
                and result.handoff.confidence < CONFIDENCE_REVIEW_THRESHOLD
            ):
                run.status = "needs_review"
                logger.warning(
                    "blueprint.low_confidence",
                    node=current_node_name,
                    confidence=result.handoff.confidence,
                    run_id=run.run_id,
                )
                break

            logger.info(
                "blueprint.node_completed",
                node=current_node_name,
                node_type=node.node_type,
                status=result.status,
                iteration=iteration,
                duration_ms=round(duration_ms, 1),
            )

            current_node_name = self._resolve_next_node(current_node_name, result)

        if run.status == "running":
            run.status = "completed" if run.qa_passed is not False else "completed_with_warnings"
        logger.info(
            "blueprint.run_completed",
            run_id=run.run_id,
            status=run.status,
            steps=steps,
            qa_passed=run.qa_passed,
        )
        return run

    def _resolve_next_node(self, current: str, result: NodeResult) -> str | None:
        """Determine the next node based on edges and result metadata."""
        # If handoff reports blocked/failed, treat as failure for routing purposes
        if result.handoff and result.handoff.status in (
            HandoffStatus.BLOCKED,
            HandoffStatus.FAILED,
        ):
            effective_status = "failed"
        else:
            effective_status = result.status

        # Check for metadata-based routing (recovery router sets route_to)
        metadata_route = None
        if hasattr(result, "details") and "route_to:" in result.details:
            metadata_route = result.details.split("route_to:")[-1].strip()

        for edge in self._definition.edges:
            if edge.from_node != current:
                continue

            if edge.condition == "success" and effective_status == "success":
                return edge.to_node
            if edge.condition == "qa_fail" and effective_status == "failed":
                return edge.to_node
            if edge.condition == "route_to" and metadata_route == edge.route_value:
                return edge.to_node
            if edge.condition == "always":
                return edge.to_node

        return None  # terminal node

    async def _build_node_context(
        self,
        node: BlueprintNode,
        run: BlueprintRun,
        brief: str,
        iteration: int,
    ) -> NodeContext:
        """Build progressively-hydrated context for a node."""
        context = NodeContext(
            html=run.html,
            brief=brief,
            iteration=iteration,
            qa_failures=list(run.qa_failures),
        )

        # Inject upstream handoff for agentic nodes (latest + full history)
        if run._last_handoff is not None:
            context.metadata["upstream_handoff"] = run._last_handoff
        if run._handoff_history:
            context.metadata["handoff_history"] = list(run._handoff_history)

        # Inject progress anchor on retries for agentic nodes
        if node.node_type == "agentic" and iteration > 0:
            context.metadata["progress_anchor"] = self._build_progress_anchor(run)

        # Inject recalled memories for agentic nodes (lazy — only if brief is present)
        if node.node_type == "agentic" and brief and self._project_id is not None:
            recalled = await self._recall_memories(brief)
            if recalled:
                context.metadata["recalled_memories"] = recalled

        # Inject component context for agentic nodes (lazy — only if HTML has refs)
        if node.node_type == "agentic" and run.html and self._component_resolver is not None:
            from app.ai.blueprints.component_context import (
                detect_component_refs,
                format_component_context,
            )

            slugs = detect_component_refs(run.html)
            if slugs:
                components = await self._component_resolver.resolve(slugs)
                if components:
                    context.metadata["component_context"] = format_component_context(components)

        # Inject graph knowledge context for agentic nodes (lazy — only if triggered)
        if node.node_type == "agentic" and self._graph_provider is not None:
            from app.ai.blueprints.graph_context import (
                format_graph_context,
                should_fetch_graph_context,
            )

            if should_fetch_graph_context(
                brief=brief,
                html=run.html,
                qa_failures=run.qa_failures,
                iteration=iteration,
            ):
                graph_results = await self._search_graph(brief)
                if graph_results:
                    context.metadata["graph_context"] = format_graph_context(graph_results)

        # Inject audience profile reference for recovery router filtering
        if self._audience_profile is not None:
            context.metadata["audience_profile"] = self._audience_profile

        # LAYER 7: Audience constraints (agentic + audience profile available)
        if node.node_type == "agentic" and self._audience_profile is not None:
            from app.ai.blueprints.audience_context import format_audience_context

            context.metadata["audience_context"] = format_audience_context(self._audience_profile)

        # LAYER 8: Project-specific subgraph context (agentic + project_id set + graph available)
        if (
            node.node_type == "agentic"
            and self._project_id is not None
            and self._graph_provider is not None
        ):
            project_subgraph = await self._search_project_subgraph(brief)
            if project_subgraph:
                context.metadata["project_subgraph"] = project_subgraph

        # LAYER 9: Competitive context (innovation node + keyword triggered)
        if node.node_type == "agentic" and node.name == "innovation":
            from app.ai.blueprints.competitor_context import (
                build_competitive_context,
                should_fetch_competitive_context,
            )

            if should_fetch_competitive_context(brief):
                competitive_ctx = build_competitive_context(brief)
                if competitive_ctx:
                    context.metadata["competitive_context"] = competitive_ctx

        return context

    async def _recall_memories(self, brief: str) -> list[dict[str, str]]:
        """Recall relevant memories from prior blueprint runs.

        Returns a list of memory dicts (content, agent, type) for injection
        into agentic node context. Failure-safe: returns empty list on errors.
        """
        try:
            from app.core.config import get_settings
            from app.core.database import get_db_context
            from app.knowledge.embedding import get_embedding_provider
            from app.memory.service import MemoryService

            async with get_db_context() as db:
                embedding_provider = get_embedding_provider(get_settings())
                memory_service = MemoryService(db, embedding_provider)
                memories = await memory_service.recall(
                    brief,
                    project_id=self._project_id,
                    limit=5,
                )
                return [
                    {
                        "content": m.content,
                        "agent": m.agent_type,
                        "type": m.memory_type,
                    }
                    for m, score in memories
                    if score > 0.3
                ]
        except Exception:
            logger.debug(
                "blueprint.memory_recall_failed",
                project_id=self._project_id,
                exc_info=True,
            )
            return []

    async def _search_graph(self, query: str) -> list["GraphSearchResult"]:
        """Search knowledge graph for structured compatibility context.

        Failure-safe: returns empty list on errors so the pipeline continues.
        """
        if self._graph_provider is None:
            return []

        try:
            results = await self._graph_provider.search(query, top_k=5)

            logger.debug(
                "blueprint.graph_search_completed",
                project_id=self._project_id,
                result_count=len(results),
            )
            return results
        except Exception:
            logger.debug(
                "blueprint.graph_search_failed",
                project_id=self._project_id,
                exc_info=True,
            )
            return []

    async def _search_project_subgraph(self, brief: str) -> str | None:
        """Search the project-specific onboarding subgraph for relevant constraints.

        Returns formatted context string or None if no results.
        Failure-safe: returns None on errors.
        """
        if self._graph_provider is None or self._project_id is None:
            return None
        try:
            dataset = f"project_onboarding_{self._project_id}"
            # dataset_name is supported by CogneeGraphProvider but not in the Protocol
            results = await self._graph_provider.search(  # type: ignore[call-arg]
                f"email client compatibility constraints for: {brief}",
                dataset_name=dataset,
                top_k=5,
            )
            if not results:
                return None

            from app.ai.blueprints.graph_context import format_graph_context

            formatted = format_graph_context(results)
            return formatted.replace(
                "--- GRAPH KNOWLEDGE CONTEXT ---",
                "--- PROJECT COMPATIBILITY CONTEXT ---",
            )
        except Exception:
            logger.debug(
                "blueprint.project_subgraph_search_failed",
                project_id=self._project_id,
                exc_info=True,
            )
            return None

    def _build_progress_anchor(self, run: BlueprintRun) -> str:
        """Build compact progress summary for agentic retry context."""
        parts: list[str] = []
        for entry in run.progress:
            if entry.status == "success":
                parts.append(f"{entry.node_name}:ok")
            else:
                parts.append(f"{entry.node_name}:{entry.summary[:60]}")
        return "[PROGRESS] " + " → ".join(parts)
