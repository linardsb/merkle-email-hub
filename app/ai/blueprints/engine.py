"""Blueprint state machine engine — routes between deterministic and agentic nodes."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

from app.ai.blueprints.exceptions import BlueprintEscalatedError, BlueprintNodeError
from app.ai.blueprints.protocols import (
    AgentHandoff,
    BlueprintNode,
    ComponentResolver,
    NodeContext,
    NodeResult,
)
from app.ai.blueprints.schemas import BlueprintProgress
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    _last_result: NodeResult | None = field(default=None, repr=False)
    _last_handoff: AgentHandoff | None = field(default=None, repr=False)


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
    ) -> None:
        self._definition = definition
        self._component_resolver = component_resolver

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
        # Check for metadata-based routing (recovery router sets route_to)
        metadata_route = None
        if hasattr(result, "details") and "route_to:" in result.details:
            metadata_route = result.details.split("route_to:")[-1].strip()

        for edge in self._definition.edges:
            if edge.from_node != current:
                continue

            if edge.condition == "success" and result.status == "success":
                return edge.to_node
            if edge.condition == "qa_fail" and result.status == "failed":
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

        # Inject upstream handoff for agentic nodes
        if run._last_handoff is not None:
            context.metadata["upstream_handoff"] = run._last_handoff

        # Inject progress anchor on retries for agentic nodes
        if node.node_type == "agentic" and iteration > 0:
            context.metadata["progress_anchor"] = self._build_progress_anchor(run)

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

        return context

    def _build_progress_anchor(self, run: BlueprintRun) -> str:
        """Build compact progress summary for agentic retry context."""
        parts: list[str] = []
        for entry in run.progress:
            if entry.status == "success":
                parts.append(f"{entry.node_name}:ok")
            else:
                parts.append(f"{entry.node_name}:{entry.summary[:60]}")
        return "[PROGRESS] " + " → ".join(parts)
