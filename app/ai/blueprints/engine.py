"""Blueprint state machine engine — routes between deterministic and agentic nodes."""

import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    from app.ai.blueprints.audience_context import AudienceProfile
    from app.ai.blueprints.checkpoint import CheckpointStore
    from app.ai.confidence_calibration import CalibrationResult
    from app.ai.recovery_outcomes import RecoveryOutcomeRepository
    from app.ai.routing import TaskTier
    from app.ai.routing_history import RoutingHistoryRepository
    from app.core.quota import BlueprintCostTracker
    from app.knowledge.graph.protocols import GraphSearchResult
    from app.projects.design_system import DesignSystem

from app.ai.agents.context_budget import (
    ECONOMY_MODE_THRESHOLD,
    compact_handoff_history,
    get_budget,
    summarize_trajectory,
)
from app.ai.agents.evals.judges.schemas import JudgeVerdict
from app.ai.blueprints.exceptions import BlueprintError, BlueprintEscalatedError, BlueprintNodeError
from app.ai.blueprints.protocols import (
    AgentHandoff,
    BlueprintNode,
    ComponentResolver,
    GraphContextProvider,
    HandoffStatus,
    NodeContext,
    NodeResult,
    StructuredFailure,
)
from app.ai.blueprints.route_advisor import RoutingDecision, RoutingPlan, build_routing_plan
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
MAX_TOTAL_STEPS = 25  # safety brake (includes repair node steps between agents and QA gate)
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
    brief_text: str = ""
    progress: list[BlueprintProgress] = field(default_factory=lambda: list[BlueprintProgress]())
    iteration_counts: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    qa_failures: list[str] = field(default_factory=lambda: list[str]())
    qa_failure_details: list[StructuredFailure] = field(
        default_factory=lambda: list[StructuredFailure]()
    )
    previous_qa_failure_details: list[StructuredFailure] = field(
        default_factory=lambda: list[StructuredFailure]()
    )
    qa_passed: bool | None = None
    judge_verdict: JudgeVerdict | None = None
    model_usage: dict[str, int] = field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )
    skipped_nodes: list[str] = field(default_factory=lambda: list[str]())
    routing_decisions: tuple[RoutingDecision, ...] = ()
    _last_result: NodeResult | None = field(default=None, repr=False)
    _last_handoff: AgentHandoff | None = field(default=None, repr=False)
    _handoff_history: list[AgentHandoff] = field(
        default_factory=lambda: list[AgentHandoff](), repr=False
    )
    resumed_from: str | None = None
    token_budget: int = 500_000
    insights_extracted: int = 0

    @property
    def remaining_budget(self) -> float:
        """Fraction of token budget remaining (0.0 to 1.0)."""
        used = self.model_usage.get("total_tokens", 0)
        if self.token_budget <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - used / self.token_budget))


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
        judge_on_retry: bool = False,
        design_system: "DesignSystem | None" = None,
        checkpoint_store: "CheckpointStore | None" = None,
        routing_history_repo: "RoutingHistoryRepository | None" = None,
        recovery_outcome_repo: "RecoveryOutcomeRepository | None" = None,
        confidence_calibrations: dict[str, "CalibrationResult"] | None = None,
        client_id: str | None = None,
    ) -> None:
        self._definition = definition
        self._component_resolver = component_resolver
        self._on_handoff = on_handoff
        self._project_id = project_id
        self._client_id = client_id
        self._graph_provider = graph_provider
        self._audience_profile = audience_profile
        self._judge_on_retry = judge_on_retry
        self._design_system = design_system
        self._checkpoint_store = checkpoint_store
        self._routing_history_repo = routing_history_repo
        self._recovery_outcome_repo = recovery_outcome_repo
        self._confidence_calibrations = confidence_calibrations

    async def run(
        self, brief: str, initial_html: str = "", user_id: int | None = None
    ) -> BlueprintRun:
        """Execute the blueprint graph from entry to terminal node."""
        from app.core.quota import BlueprintCostTracker

        run = BlueprintRun(html=initial_html, brief_text=brief)

        # Build routing plan before main loop (deterministic, no I/O)
        routing_plan = build_routing_plan(
            node_names=list(self._definition.nodes.keys()),
            audience_profile=self._audience_profile,
            html=initial_html,
            brief=brief,
        )
        run.routing_decisions = routing_plan.decisions

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

        return await self._execute_from(
            run, self._definition.entry_node, brief, routing_plan, cost_tracker, user_id
        )

    async def resume(self, run_id: str, brief: str, user_id: int | None = None) -> BlueprintRun:
        """Resume a blueprint run from its latest checkpoint.

        Loads the latest checkpoint, validates the blueprint definition hasn't
        changed incompatibly, and continues execution from the next unfinished node.
        """
        if self._checkpoint_store is None:
            raise BlueprintError("Checkpoints are not enabled — cannot resume")

        from app.ai.blueprints.checkpoint import restore_run

        data = await self._checkpoint_store.load_latest(run_id)
        if data is None:
            raise BlueprintError(f"No checkpoint found for run {run_id}")

        # Validate blueprint name matches
        if data.blueprint_name != self._definition.name:
            raise BlueprintError(
                f"Blueprint mismatch: checkpoint is for '{data.blueprint_name}', "
                f"but engine has '{self._definition.name}'"
            )

        # Validate next node exists in current definition
        next_node = data.next_node_name
        if next_node is not None and next_node not in self._definition.nodes:
            raise BlueprintError(
                f"Blueprint definition changed: node '{next_node}' no longer exists"
            )

        run = restore_run(data)
        run.resumed_from = data.node_name

        # Terminal checkpoint — nothing left to execute
        if next_node is None:
            if run.status == "running":
                run.status = (
                    "completed" if run.qa_passed is not False else "completed_with_warnings"
                )
            logger.info(
                "blueprint.resume_terminal",
                run_id=run_id,
                node_name=data.node_name,
            )
            return run

        # Build routing plan for remaining nodes
        routing_plan = build_routing_plan(
            node_names=list(self._definition.nodes.keys()),
            audience_profile=self._audience_profile,
            html=run.html,
            brief=brief,
        )
        run.routing_decisions = routing_plan.decisions

        # Set up cost tracking
        from app.core.quota import BlueprintCostTracker

        cost_tracker: BlueprintCostTracker | None = None
        if user_id is not None:
            from app.core.config import get_settings as _get_settings

            _settings = _get_settings()
            cost_tracker = BlueprintCostTracker(daily_cap=_settings.blueprint.daily_token_cap)

        logger.info(
            "blueprint.run_resumed",
            run_id=run_id,
            checkpoint_node=data.node_name,
            next_node=next_node,
            blueprint=self._definition.name,
        )

        return await self._execute_from(run, next_node, brief, routing_plan, cost_tracker, user_id)

    async def _execute_from(
        self,
        run: BlueprintRun,
        start_node: str | None,
        brief: str,
        routing_plan: RoutingPlan,
        cost_tracker: "BlueprintCostTracker | None" = None,
        user_id: int | None = None,
    ) -> BlueprintRun:
        """Execute the blueprint graph starting from ``start_node``.

        Shared by :meth:`run` (from entry) and :meth:`resume` (from checkpoint).
        """
        current_node_name = start_node
        steps = 0

        while current_node_name is not None and steps < MAX_TOTAL_STEPS:
            steps += 1
            node = self._definition.nodes[current_node_name]

            # Track iteration count for agentic nodes
            iteration = run.iteration_counts.get(current_node_name, 0)
            if node.node_type == "agentic" and iteration >= MAX_SELF_CORRECTION_ROUNDS:
                raise BlueprintEscalatedError(current_node_name, iteration)

            # Skip irrelevant agentic nodes based on routing plan
            if (
                node.node_type == "agentic"
                and not routing_plan.force_full
                and current_node_name in routing_plan.skip_nodes
            ):
                logger.info(
                    "blueprint.node_skipped",
                    node=current_node_name,
                    run_id=run.run_id,
                    reason="routing_plan_skip",
                )
                run.skipped_nodes.append(current_node_name)
                run.progress.append(
                    BlueprintProgress(
                        node_name=current_node_name,
                        node_type=node.node_type,
                        status="skipped",
                        iteration=iteration,
                        summary=_skip_summary(current_node_name, routing_plan),
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

            # Scope validation: reject out-of-scope fixer changes on retry
            if node.node_type == "agentic" and iteration > 0 and run.html and result.html:
                from app.ai.blueprints.nodes.recovery_router_node import AGENT_SCOPES
                from app.ai.blueprints.scope_validator import validate_scope

                agent_scope = AGENT_SCOPES.get(current_node_name)
                if agent_scope is not None:
                    violations = validate_scope(
                        pre_html=run.html,
                        post_html=result.html,
                        scope=agent_scope,
                        agent_name=current_node_name,
                    )
                    if violations:
                        logger.warning(
                            "blueprint.scope_violation",
                            agent=current_node_name,
                            violations=[v.description for v in violations],
                            run_id=run.run_id,
                        )
                        # Reject the change — keep pre-fix HTML, escalate
                        result = NodeResult(
                            status="failed",
                            html=run.html,
                            details=f"scope_violation:{current_node_name}",
                            error=f"Scope violation: {violations[0].description}",
                        )

            # --- Inline judge on recovery retries ---
            if (
                self._judge_on_retry
                and node.node_type == "agentic"
                and iteration > 0
                and result.status == "success"
                and result.html
            ):
                from app.ai.blueprints.inline_judge import run_inline_judge

                agent_name = node.name.removesuffix("_node")
                verdict = await run_inline_judge(
                    agent_name=agent_name,
                    context=context,
                    html_output=result.html,
                    run=run,
                )
                if verdict is not None:
                    run.judge_verdict = verdict

                    # Persist verdict for aggregation (fire-and-forget)
                    from app.core.config import get_settings as _get_settings_ja

                    if _get_settings_ja().blueprint.judge_aggregation_enabled:
                        try:
                            from app.ai.blueprints.judge_aggregator import persist_judge_verdict

                            await persist_judge_verdict(verdict, self._project_id, run.run_id)
                        except Exception:
                            logger.debug(
                                "blueprint.judge_verdict_persist_failed",
                                run_id=run.run_id,
                                exc_info=True,
                            )

                    if not verdict.overall_pass:
                        run.status = "needs_review"
                        logger.warning(
                            "blueprint.inline_judge_rejected",
                            agent=agent_name,
                            run_id=run.run_id,
                            failed_criteria=[
                                cr.criterion for cr in verdict.criteria_results if not cr.passed
                            ],
                        )
                        break
                    logger.info(
                        "blueprint.inline_judge_approved",
                        agent=agent_name,
                        run_id=run.run_id,
                    )

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
                    await cost_tracker.record_usage(user_id, node_tokens)
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

            # Track QA results
            if current_node_name == "qa_gate":
                if result.status == "success":
                    run.qa_passed = True
                    run.qa_failures = []
                    run.qa_failure_details = []
                else:
                    run.qa_passed = False
                    run.qa_failures = [
                        line.strip() for line in result.details.split("\n") if line.strip()
                    ]
                    # Save previous failures for cycle detection before updating
                    run.previous_qa_failure_details = list(run.qa_failure_details)
                    run.qa_failure_details = list(result.structured_failures)

                # Record recovery outcomes (fire-and-forget)
                if self._recovery_outcome_repo is not None:
                    try:
                        await self._record_recovery_outcomes(run)
                    except Exception:
                        logger.debug(
                            "blueprint.recovery_outcome_record_failed",
                            run_id=run.run_id,
                            exc_info=True,
                        )

                # Store correction example on successful recovery (fire-and-forget)
                if result.status == "success" and run._handoff_history:
                    from app.core.config import get_settings as _get_settings_ce

                    if _get_settings_ce().blueprint.correction_examples_enabled:
                        try:
                            await self._store_correction_example(run)
                        except Exception:
                            logger.debug(
                                "blueprint.correction_example_store_failed",
                                run_id=run.run_id,
                                exc_info=True,
                            )

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

            # LAYER 18: Correction pattern tracking (fire-and-forget)
            if (
                node.node_type == "agentic"
                and context.html
                and result.html
                and context.html != result.html
                and result.handoff is not None
            ):
                from app.core.config import get_settings as _get_settings_ct

                if _get_settings_ct().correction_tracker.enabled:
                    try:
                        from app.design_sync.correction_tracker import CorrectionTracker

                        tracker = CorrectionTracker(data_dir=Path("data"))
                        await tracker.record_correction(
                            agent=result.handoff.agent_name,
                            original_html=context.html,
                            corrected_html=result.html,
                        )
                    except Exception:
                        logger.debug(
                            "blueprint.correction_tracker_failed",
                            node=current_node_name,
                            run_id=run.run_id,
                            exc_info=True,
                        )

            # Low confidence → route to human review instead of retrying
            if (
                node.node_type == "agentic"
                and result.handoff is not None
                and result.handoff.confidence is not None
            ):
                effective_threshold = CONFIDENCE_REVIEW_THRESHOLD
                if self._confidence_calibrations is not None:
                    cal = self._confidence_calibrations.get(current_node_name)
                    if cal is not None:
                        effective_threshold = cal.effective_threshold

                if result.handoff.confidence < effective_threshold:
                    run.status = "needs_review"
                    logger.warning(
                        "blueprint.low_confidence",
                        node=current_node_name,
                        confidence=result.handoff.confidence,
                        threshold=effective_threshold,
                        calibrated=self._confidence_calibrations is not None
                        and current_node_name in (self._confidence_calibrations or {}),
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

            # Resolve next node BEFORE checkpoint so checkpoint records where to resume
            next_node = self._resolve_next_node(current_node_name, result)

            # Fire-and-forget checkpoint after successful node
            await self._save_checkpoint(
                run, current_node_name, len(run.progress) - 1, next_node_name=next_node
            )

            # Fire-and-forget routing history entry
            if self._routing_history_repo is not None and node.node_type == "agentic":
                try:
                    accepted = result.status == "success"
                    agent_tier: TaskTier = getattr(node, "model_tier", "standard")
                    await self._routing_history_repo.record(
                        agent_name=current_node_name,
                        project_id=self._project_id,
                        tier_used=agent_tier,
                        accepted=accepted,
                    )
                except Exception:
                    logger.debug(
                        "blueprint.routing_history_record_failed",
                        node=current_node_name,
                        run_id=run.run_id,
                        exc_info=True,
                    )

            current_node_name = next_node

        if run.status == "running":
            run.status = "completed" if run.qa_passed is not False else "completed_with_warnings"
        logger.info(
            "blueprint.run_completed",
            run_id=run.run_id,
            status=run.status,
            steps=steps,
            qa_passed=run.qa_passed,
        )

        # Notify on terminal status
        from app.notifications.channels import Notification
        from app.notifications.emitter import emit_notification

        if run.status in ("completed", "completed_with_warnings"):
            await emit_notification(
                Notification(
                    event="blueprint.run_completed",
                    severity="info",
                    title="Blueprint run completed",
                    body=f"Blueprint run {run.run_id} completed ({run.status})",
                    project_id=self._project_id,
                    metadata={"run_id": run.run_id, "status": run.status},
                )
            )
        elif run.status in ("needs_review", "cost_cap_exceeded"):
            await emit_notification(
                Notification(
                    event="blueprint.run_failed",
                    severity="error",
                    title="Blueprint run failed",
                    body=f"Blueprint run {run.run_id}: {run.status}",
                    project_id=self._project_id,
                    metadata={"run_id": run.run_id, "status": run.status},
                )
            )

        return run

    async def _save_checkpoint(
        self,
        run: BlueprintRun,
        node_name: str,
        node_index: int,
        next_node_name: str | None = None,
    ) -> None:
        """Fire-and-forget checkpoint save after a successful node."""
        if self._checkpoint_store is None:
            return
        try:
            from app.ai.blueprints.checkpoint import serialize_run

            data = serialize_run(
                run,
                node_name=node_name,
                node_index=node_index,
                blueprint_name=self._definition.name,
                next_node_name=next_node_name,
            )
            await self._checkpoint_store.save(data)
        except Exception:
            logger.warning(
                "blueprint.checkpoint_save_failed",
                node=node_name,
                run_id=run.run_id,
                exc_info=True,
            )

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

        # Context budget: determine economy mode + per-agent budget
        economy = run.remaining_budget < ECONOMY_MODE_THRESHOLD
        agent_name = node.name.removesuffix("_node")
        agent_budget = get_budget(agent_name)
        context.metadata["agent_name"] = agent_name
        context.metadata["agent_budget"] = agent_budget
        if self._client_id:
            context.metadata["client_id"] = self._client_id

        # Inject upstream handoff for agentic nodes (compact in economy mode)
        if run._last_handoff is not None:
            context.metadata["upstream_handoff"] = (
                run._last_handoff.compact() if economy else run._last_handoff
            )

            # Inject formatted upstream constraints for agentic nodes
            if node.node_type == "agentic":
                from app.ai.blueprints.handoff import format_upstream_constraints

                upstream_constraints = format_upstream_constraints(run._last_handoff)
                if upstream_constraints:
                    context.metadata["upstream_constraints"] = upstream_constraints

                # Inject learnings from upstream agent (within-run propagation)
                if run._last_handoff.learnings:
                    context.metadata["upstream_learnings"] = run._last_handoff.learnings

        if run._handoff_history:
            # Enable decay tiers when history is long enough (Phase 3)
            use_decay = len(run._handoff_history) >= 4
            context.metadata["handoff_history"] = compact_handoff_history(
                run._handoff_history, economy=economy, decay_tiers=use_decay
            )

        # Inject structured QA failure details (compact in economy mode)
        if run.qa_failure_details:
            context.metadata["qa_failure_details"] = (
                [f.compact() for f in run.qa_failure_details]
                if economy
                else list(run.qa_failure_details)
            )
        if run.previous_qa_failure_details:
            context.metadata["previous_qa_failure_details"] = list(run.previous_qa_failure_details)

        # Economy mode: inject trajectory summary and flag
        if economy:
            context.metadata["trajectory_summary"] = summarize_trajectory(run)
            context.metadata["economy_mode"] = True

        # Inject progress anchor on retries for agentic nodes
        if node.node_type == "agentic" and iteration > 0:
            context.metadata["progress_anchor"] = self._build_progress_anchor(run)

        # LAYER 15: Correction examples (agentic + retry + feature enabled)
        if node.node_type == "agentic" and iteration > 0:
            from app.core.config import get_settings as _get_settings_ce2

            if _get_settings_ce2().blueprint.correction_examples_enabled:
                from app.ai.blueprints.correction_examples import (
                    format_correction_examples,
                    recall_correction_examples,
                )

                try:
                    examples = await recall_correction_examples(
                        agent_name=agent_name,
                        qa_failures=run.qa_failures,
                        project_id=self._project_id,
                    )
                    if examples:
                        context.metadata["correction_examples"] = format_correction_examples(
                            examples
                        )
                except Exception:
                    logger.debug(
                        "blueprint.correction_recall_failed",
                        node=node.name,
                        exc_info=True,
                    )

        # LAYER 16: Judge-derived prompt patches (agentic + aggregation enabled)
        if node.node_type == "agentic":
            from app.core.config import get_settings as _get_settings_ja2

            if _get_settings_ja2().blueprint.judge_aggregation_enabled:
                from app.ai.blueprints.judge_aggregator import (
                    aggregate_verdicts,
                    format_prompt_patches,
                )

                try:
                    patches = await aggregate_verdicts(agent_name, self._project_id)
                    if patches:
                        context.metadata["prompt_patches"] = format_prompt_patches(patches)
                except Exception:
                    logger.debug(
                        "blueprint.judge_aggregation_inject_failed",
                        node=node.name,
                        exc_info=True,
                    )

        # LAYER 17: Cross-agent insight propagation (agentic + enabled + audience)
        if node.node_type == "agentic" and self._audience_profile is not None:
            from app.core.config import get_settings as _get_settings_ip

            if _get_settings_ip().blueprint.insight_propagation_enabled:
                from app.ai.blueprints.insight_bus import (
                    format_insight_context,
                    recall_insights,
                )

                try:
                    audience_client_ids = tuple(self._audience_profile.client_ids)
                    insights = await recall_insights(
                        agent_name=agent_name,
                        client_ids=audience_client_ids,
                        project_id=self._project_id,
                    )
                    if insights:
                        context.metadata["cross_agent_insights"] = format_insight_context(insights)
                        logger.info(
                            "blueprint.insights_injected",
                            agent=agent_name,
                            count=len(insights),
                        )
                except Exception:
                    logger.debug(
                        "blueprint.insight_recall_failed",
                        node=node.name,
                        exc_info=True,
                    )

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

        # Inject recovery outcome repo for adaptive routing in recovery router
        if self._recovery_outcome_repo is not None:
            context.metadata["recovery_outcome_repo"] = self._recovery_outcome_repo
            context.metadata["project_id"] = self._project_id

        # Inject audience profile reference for recovery router filtering
        if self._audience_profile is not None:
            context.metadata["audience_profile"] = self._audience_profile

        # LAYER 7: Audience constraints (agentic + audience profile available)
        if node.node_type == "agentic" and self._audience_profile is not None:
            from app.ai.blueprints.audience_context import format_audience_context

            context.metadata["audience_context"] = format_audience_context(self._audience_profile)
            context.metadata["audience_client_ids"] = tuple(self._audience_profile.client_ids)

        # LAYER 8: Project-specific subgraph context (agentic + project_id set + graph available)
        if (
            node.node_type == "agentic"
            and self._project_id is not None
            and self._graph_provider is not None
        ):
            project_subgraph = await self._search_project_subgraph(brief)
            if project_subgraph:
                context.metadata["project_subgraph"] = project_subgraph

        # LAYER 9: Cross-agent failure patterns (agentic + audience profile available)
        if node.node_type == "agentic" and self._audience_profile is not None:
            from app.ai.blueprints.failure_patterns import recall_failure_patterns

            agent_for_node = node.name.removesuffix("_node")
            failure_context = await recall_failure_patterns(
                agent_name=agent_for_node,
                client_ids=self._audience_profile.client_ids,
                project_id=self._project_id,
            )
            if failure_context:
                context.metadata["failure_patterns"] = failure_context

        # LAYER 10: Competitive context (innovation node + keyword triggered)
        if node.node_type == "agentic" and node.name == "innovation":
            from app.ai.blueprints.competitor_context import (
                build_competitive_context,
                should_fetch_competitive_context,
            )

            if should_fetch_competitive_context(brief):
                # Use audience-aware feasibility when audience profile available
                _audience_client_ids: tuple[str, ...] = tuple(  # pyright: ignore[reportUnknownVariableType]
                    context.metadata.get("audience_client_ids", ())  # type: ignore[arg-type]  # pyright: ignore[reportUnknownArgumentType]
                )
                if _audience_client_ids:
                    from app.knowledge.ontology.competitive_feasibility import (
                        format_feasibility_context,
                    )

                    competitive_ctx = format_feasibility_context(
                        client_ids=_audience_client_ids,
                        technique=brief,
                    )
                else:
                    competitive_ctx = build_competitive_context(brief)

                if competitive_ctx:
                    context.metadata["competitive_context"] = competitive_ctx

        # LAYER 11.5: Client lookup tools (agentic — deterministic matrix queries)
        if node.node_type == "agentic":
            from app.ai.agents.tools.client_lookup import (
                _CLIENT_LOOKUP_TOOL,
                _MULTI_CLIENT_LOOKUP_TOOL,
            )

            context.metadata["client_lookup_tool"] = _CLIENT_LOOKUP_TOOL
            context.metadata["client_lookup_batch_tool"] = _MULTI_CLIENT_LOOKUP_TOOL

        # LAYER 12: Adaptive model tier (agentic only — inject effective tier for model selection)
        if self._routing_history_repo is not None and node.node_type == "agentic":
            from app.ai.routing_history import resolve_adaptive_tier

            try:
                default_tier: TaskTier = getattr(node, "model_tier", "standard")
                effective_tier = await resolve_adaptive_tier(
                    default_tier,
                    node.name,
                    self._project_id,
                    self._routing_history_repo,
                )
                context.metadata["effective_tier"] = effective_tier
                context.metadata["default_tier"] = default_tier
            except Exception:
                logger.debug("blueprint.adaptive_tier_failed", node=node.name, exc_info=True)

        # LAYER 13: Knowledge prefetch (agentic + graph available + prefetch enabled)
        if (
            node.node_type == "agentic"
            and self._graph_provider is not None
            and self._project_id is not None
        ):
            from app.core.config import get_settings as _get_settings

            _settings = _get_settings()
            if _settings.cognee.prefetch_enabled:
                from app.ai.agents.knowledge_prefetch import (
                    format_prefetch_context,
                    prefetch_prior_outcomes,
                )

                try:
                    prefetch_results = await prefetch_prior_outcomes(
                        agent_name=agent_name,
                        brief=brief,
                        project_id=self._project_id,
                        graph_provider=self._graph_provider,
                        top_k=_settings.cognee.prefetch_top_k,
                        min_score=_settings.cognee.prefetch_min_score,
                        cache_ttl=_settings.cognee.prefetch_ttl_seconds,
                    )
                    if prefetch_results:
                        context.metadata["knowledge_prefetch"] = format_prefetch_context(
                            prefetch_results
                        )
                except Exception:
                    logger.debug(
                        "blueprint.knowledge_prefetch_failed",
                        node=node.name,
                        project_id=self._project_id,
                        exc_info=True,
                    )

        # LAYER 14: Multimodal context (feature-gated, agentic nodes only)
        from app.core.config import get_settings as _get_settings_l14

        _settings_l14 = _get_settings_l14()
        if _settings_l14.ai.multimodal_context_enabled and node.node_type == "agentic":
            from app.ai.multimodal import ContentBlock, ImageBlock, TextBlock

            multimodal_blocks: list[ContentBlock] = []

            # Scaffolder: inject design import screenshots (Phase 12 assets)
            if node.name == "scaffolder":
                design_import_assets: list[dict[str, object]] = context.metadata.get(  # type: ignore[assignment]
                    "design_import_assets", []
                )
                for asset in design_import_assets:
                    raw_image = asset.get("image_bytes")
                    if isinstance(raw_image, bytes):
                        multimodal_blocks.append(
                            ImageBlock(
                                data=raw_image,
                                media_type=str(asset.get("media_type", "image/png")),
                                source="base64",
                            )
                        )

            # Visual QA: convert metadata screenshots to ImageBlocks
            if node.name == "visual_qa":
                import base64 as _b64

                screenshots_dict: dict[str, str] = context.metadata.get("screenshots", {})  # type: ignore[assignment]
                for client_name, b64_data in screenshots_dict.items():
                    try:
                        image_bytes = _b64.b64decode(b64_data)
                        multimodal_blocks.append(
                            ImageBlock(data=image_bytes, media_type="image/png", source="base64")
                        )
                        multimodal_blocks.append(TextBlock(text=f"[Screenshot: {client_name}]"))
                    except Exception:
                        logger.warning(
                            "blueprint.multimodal_context.invalid_screenshot",
                            client=client_name,
                            exc_info=True,
                        )

            if multimodal_blocks:
                from app.ai.multimodal import validate_content_blocks

                try:
                    validate_content_blocks(multimodal_blocks)
                    context.multimodal_context = multimodal_blocks
                except Exception:
                    logger.warning(
                        "blueprint.multimodal_context.validation_failed",
                        node=node.name,
                        block_count=len(multimodal_blocks),
                        exc_info=True,
                    )

        # LAYER 14.5: Visual defect multimodal override (recovery router injects screenshots for fixers)
        override_raw = context.metadata.get("multimodal_context_override")
        if isinstance(override_raw, list) and override_raw and node.node_type == "agentic":
            from app.ai.multimodal import ContentBlock

            typed_blocks: list[ContentBlock] = [
                b
                for b in cast(list[Any], override_raw)  # type: ignore[redundant-cast]
                if isinstance(b, ContentBlock)
            ]
            if typed_blocks:
                existing = context.multimodal_context or []
                context.multimodal_context = [*existing, *typed_blocks]
            # Clear override after injection (one-shot)
            context.metadata.pop("multimodal_context_override", None)

        # LAYER 11: Design system (ALL nodes — agentic for prompt context, deterministic for brand repair)
        if self._design_system is not None:
            from app.projects.design_system import (
                design_system_to_brand_rules,
                resolve_color_map,
                resolve_font_map,
            )

            context.metadata["design_system"] = self._design_system
            context.metadata["design_system_brand_rules"] = design_system_to_brand_rules(
                self._design_system
            )
            context.metadata["ds_color_map"] = resolve_color_map(self._design_system)
            context.metadata["ds_font_map"] = resolve_font_map(self._design_system)

        # LAYER 18: Prompt injection scan on user-supplied fields
        from app.core.config import get_settings as _get_settings_pg

        _settings_pg = _get_settings_pg()
        if _settings_pg.security.prompt_guard_enabled:
            from app.ai.security.prompt_guard import scan_for_injection

            _pg_mode = _settings_pg.security.prompt_guard_mode
            for _field_name, _field_val in [
                ("brief", brief),
                ("html", context.html),
            ]:
                if _field_val:
                    _scan = scan_for_injection(_field_val, mode=_pg_mode)
                    if not _scan.clean:
                        logger.warning(
                            "security.prompt_injection_detected",
                            field=_field_name,
                            flags=_scan.flags,
                            agent=agent_name,
                        )
                        if _pg_mode == "strip" and _scan.sanitized is not None:
                            if _field_name == "brief":
                                context.brief = _scan.sanitized
                            elif _field_name == "html":
                                context.html = _scan.sanitized

            for _meta_key in ("qa_failure_details", "graph_context"):
                _meta_val = context.metadata.get(_meta_key)
                if isinstance(_meta_val, str):
                    _scan = scan_for_injection(_meta_val, mode=_pg_mode)
                    if not _scan.clean and _pg_mode == "strip" and _scan.sanitized is not None:
                        context.metadata[_meta_key] = _scan.sanitized

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

    async def _record_recovery_outcomes(self, run: BlueprintRun) -> None:
        """Record recovery outcomes for each fixer that ran before this QA gate.

        Cross-references handoff history with QA results to determine which
        fixes succeeded and which failed. Fire-and-forget safe.
        """
        if self._recovery_outcome_repo is None or not run._handoff_history:
            return

        from app.ai.blueprints.nodes.recovery_router_node import CHECK_TO_AGENT, _fingerprint

        # Build set of still-failing checks
        still_failing: set[str] = set()
        for sf in run.qa_failure_details:
            still_failing.add(sf.check_name)

        # For each previous QA failure that a fixer was routed to address
        for prev_sf in run.previous_qa_failure_details:
            agent = prev_sf.suggested_agent or CHECK_TO_AGENT.get(prev_sf.check_name)
            if agent is None:
                continue

            # Check if this agent actually ran (is in handoff history)
            ran = any(h.agent_name == agent for h in run._handoff_history)
            if not ran:
                continue

            resolved = prev_sf.check_name not in still_failing
            await self._recovery_outcome_repo.record(
                check_name=prev_sf.check_name,
                agent_routed=agent,
                failure_fingerprint=_fingerprint(prev_sf),
                resolved=resolved,
                iterations_needed=run.iteration_counts.get(f"{agent}_node", 1),
                run_id=run.run_id,
                project_id=self._project_id,
            )

    async def _store_correction_example(self, run: BlueprintRun) -> None:
        """Store the last successful correction as a few-shot example.

        Called when QA passes after a recovery cycle. Fire-and-forget safe.
        """
        if not run._handoff_history or not run.previous_qa_failure_details:
            return

        from app.ai.blueprints.correction_examples import store_correction_example

        last_handoff = run._handoff_history[-1]
        failure_desc = "; ".join(
            f"{sf.check_name}: {sf.details[:100]}" for sf in run.previous_qa_failure_details[:3]
        )
        correction_summary = "; ".join(last_handoff.decisions[:3]) if last_handoff.decisions else ""

        if not correction_summary:
            return

        check_name = (
            run.previous_qa_failure_details[0].check_name
            if run.previous_qa_failure_details
            else "unknown"
        )

        await store_correction_example(
            agent_name=last_handoff.agent_name,
            check_name=check_name,
            failure_description=failure_desc,
            correction_summary=correction_summary,
            project_id=self._project_id,
            run_id=run.run_id,
        )

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
            results = await self._graph_provider.search(  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]
                f"email client compatibility constraints for: {brief}",
                dataset_name=dataset,  # pyright: ignore[reportCallIssue]
                top_k=5,
            )
            if not results:
                return None

            from app.ai.blueprints.graph_context import format_graph_context

            formatted = format_graph_context(results)  # pyright: ignore[reportUnknownArgumentType]
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


def _skip_summary(node_name: str, plan: RoutingPlan) -> str:
    """Get the skip reason from routing plan for the progress log."""
    for d in plan.decisions:
        if d.node_name == node_name and d.action.value == "skip":
            return f"Skipped: {d.reason}"
    return "Skipped: not relevant for target audience"


def _make_pipeline_checkpoint_adapter(
    store: "CheckpointStore",
    blueprint_name: str,
) -> object:
    """Adapt blueprint CheckpointStore to PipelineCheckpointCallback interface.

    Stores pipeline pass checkpoints in the same ``blueprint_checkpoints`` table
    using compound node names (``scaffolder:<pass_name>``) and a +100 node_index
    offset to avoid collision with node-level checkpoints.
    """
    import hashlib

    from sqlalchemy import select

    from app.ai.agents.scaffolder.pipeline_checkpoint import PipelineCheckpoint
    from app.ai.blueprints.checkpoint_models import BlueprintCheckpoint

    class _Adapter:
        async def save_pass(self, checkpoint: PipelineCheckpoint) -> None:
            data_dict = {"pipeline_pass": checkpoint.pass_name, "pipeline_data": checkpoint.data}
            row = BlueprintCheckpoint(
                run_id=checkpoint.run_id,
                blueprint_name=blueprint_name,
                node_name=f"scaffolder:{checkpoint.pass_name}",
                node_index=checkpoint.pass_index + 100,
                state_json=data_dict,
                html_hash=hashlib.sha256(b"").hexdigest(),
            )
            store._db.add(row)  # type: ignore[attr-defined]
            await store._db.commit()  # type: ignore[attr-defined]

        async def load_passes(self, run_id: str) -> list[PipelineCheckpoint]:
            stmt = (
                select(BlueprintCheckpoint)
                .where(
                    BlueprintCheckpoint.run_id == run_id,
                    BlueprintCheckpoint.node_name.like("scaffolder:%"),
                    BlueprintCheckpoint.node_index >= 100,
                )
                .order_by(BlueprintCheckpoint.node_index.asc())
            )
            raw_result: Any = await store._db.execute(stmt)  # type: ignore[attr-defined]
            rows: list[BlueprintCheckpoint] = list(raw_result.scalars().all())  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
            return [
                PipelineCheckpoint(
                    run_id=run_id,
                    pass_name=row.state_json["pipeline_pass"],
                    pass_index=row.node_index - 100,
                    data=row.state_json["pipeline_data"],
                )
                for row in rows
            ]

    return _Adapter()
