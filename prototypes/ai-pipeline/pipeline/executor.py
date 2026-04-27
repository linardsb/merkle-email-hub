"""Concurrent pipeline executor with topological ordering."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.ai.pipeline.adapters import ADAPTER_REGISTRY
from app.ai.pipeline.artifacts import (
    ArtifactStore,
    BuildPlanArtifact,
    HtmlArtifact,
    ProactiveWarningsArtifact,
)
from app.ai.pipeline.contracts import ContractValidator, load_contract
from app.ai.pipeline.dag import PipelineDag
from app.core.config import PipelineConfig
from app.core.exceptions import HookAbortError, PipelineExecutionError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.ai.hooks.registry import HookEvent, HookRegistry

logger = get_logger(__name__)

CONTRACT_DEF_DIR = Path(__file__).parent / "contract_defs"


@dataclass(frozen=True, slots=True)
class NodeTrace:
    """Execution trace for a single pipeline node."""

    agent_name: str
    duration_ms: int
    tokens_used: int = 0
    contract_passed: bool | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Outcome of a complete pipeline execution."""

    artifacts: dict[str, str]  # name -> type snapshot
    trace: tuple[NodeTrace, ...]
    total_duration_ms: int
    levels_executed: int
    nodes_executed: int
    cost_tokens: int


@runtime_checkable
class AgentRunner(Protocol):
    """Callable that runs an agent with adapted inputs and returns a response."""

    async def __call__(self, agent_name: str, inputs: dict[str, object]) -> object: ...


class PipelineExecutor:
    """Executes a PipelineDag with concurrent same-level agent invocation."""

    def __init__(
        self,
        dag: PipelineDag,
        store: ArtifactStore,
        settings: PipelineConfig,
        agent_runner: AgentRunner,
        contract_validator: ContractValidator | None = None,
        hook_registry: HookRegistry | None = None,
    ) -> None:
        self._dag = dag
        self._store = store
        self._settings = settings
        self._runner = agent_runner
        self._validator = contract_validator or ContractValidator()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_agents)
        self._hooks = hook_registry
        self._current_run_id = ""

    async def _fire(
        self,
        event: HookEvent,
        *,
        agent_name: str | None = None,
        level: int | None = None,
        artifacts: ArtifactStore | None = None,
        node_trace: object | None = None,
        cost_tokens: int = 0,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Fire a hook event if a registry is configured."""
        if self._hooks is None:
            return
        from app.ai.hooks.registry import HookContext

        ctx = HookContext(
            run_id=self._current_run_id,
            pipeline_name=self._dag.name,
            event=event,
            agent_name=agent_name,
            level=level,
            artifacts=artifacts,
            node_trace=node_trace,
            cost_tokens=cost_tokens,
            metadata=metadata or {},
        )
        await self._hooks.fire(event, ctx)

    async def execute(self, run_id: str, completed_levels: int = 0) -> PipelineResult:
        """Run all DAG levels, executing same-level nodes concurrently."""
        from app.ai.hooks.registry import HookEvent

        self._current_run_id = run_id
        start = time.monotonic()
        levels = self._dag.topological_levels()
        traces: list[NodeTrace] = []
        nodes_executed = 0
        total_tokens = 0

        # Inject proactive warnings before first level
        await self._inject_proactive_warnings(run_id)

        # Fire PRE_PIPELINE
        await self._fire(
            HookEvent.PRE_PIPELINE,
            metadata={"total_levels": len(levels)},
            artifacts=self._store,
        )

        for lvl_idx, node_ids in enumerate(levels):
            if lvl_idx < completed_levels:
                logger.info(
                    "pipeline.level.skipped",
                    extra={"run_id": run_id, "level": lvl_idx},
                )
                continue

            logger.info(
                "pipeline.level.start",
                extra={"run_id": run_id, "level": lvl_idx, "nodes": node_ids},
            )

            # Fire PRE_LEVEL
            await self._fire(HookEvent.PRE_LEVEL, level=lvl_idx, artifacts=self._store)

            # Run all nodes at this level concurrently
            tasks = [self._run_node(node_id, run_id) for node_id in node_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results — re-raise HookAbortError immediately
            level_traces: list[NodeTrace] = []
            for node_id, result in zip(node_ids, results, strict=True):
                if isinstance(result, HookAbortError):
                    raise result
                if isinstance(result, BaseException):
                    trace = NodeTrace(
                        agent_name=self._dag.nodes[node_id].agent_name,
                        duration_ms=0,
                        error=str(result),
                    )
                    level_traces.append(trace)
                    logger.error(
                        "pipeline.node.failed",
                        extra={
                            "run_id": run_id,
                            "node": node_id,
                            "error": str(result),
                        },
                    )
                else:
                    level_traces.append(result)
                    total_tokens += result.tokens_used

            traces.extend(level_traces)
            nodes_executed += len(node_ids)

            # Merge HTML outputs if multiple nodes at this level produce HTML variants
            self._merge_html_outputs(node_ids)

            logger.info(
                "pipeline.level.complete",
                extra={
                    "run_id": run_id,
                    "level": lvl_idx,
                    "errors": sum(1 for t in level_traces if t.error),
                },
            )

            # Fire POST_LEVEL
            await self._fire(
                HookEvent.POST_LEVEL,
                level=lvl_idx,
                metadata={"total_levels": len(levels)},
                artifacts=self._store,
            )

            # Fail-fast on strict mode if any node failed
            if self._settings.contract_strict and any(t.error for t in level_traces):
                break

        elapsed = int((time.monotonic() - start) * 1000)

        # Fire POST_PIPELINE
        await self._fire(
            HookEvent.POST_PIPELINE,
            cost_tokens=total_tokens,
            metadata={"traces": traces, "total_levels": len(levels)},
            artifacts=self._store,
        )

        return PipelineResult(
            artifacts=self._store.snapshot(),
            trace=tuple(traces),
            total_duration_ms=elapsed,
            levels_executed=min(len(levels), len(levels) - completed_levels),
            nodes_executed=nodes_executed,
            cost_tokens=total_tokens,
        )

    async def _run_node(self, node_id: str, run_id: str) -> NodeTrace:
        """Execute a single node: adapt inputs -> run agent -> adapt outputs -> validate."""
        from app.ai.hooks.registry import HookEvent

        node = self._dag.nodes[node_id]
        adapter = ADAPTER_REGISTRY.get(node.agent_name)
        start = time.monotonic()

        async with self._semaphore:
            logger.info(
                "pipeline.node.start",
                extra={
                    "run_id": run_id,
                    "node": node_id,
                    "agent": node.agent_name,
                },
            )

            try:
                # Fire PRE_AGENT
                await self._fire(
                    HookEvent.PRE_AGENT,
                    agent_name=node.agent_name,
                    artifacts=self._store,
                )

                # Adapt inputs from artifact store
                inputs = adapter.adapt_inputs(self._store) if adapter else {}

                # Run agent via injected runner
                response = await self._runner(node.agent_name, inputs)

                # Adapt outputs back to artifact store
                if adapter:
                    adapter.adapt_outputs(response, self._store)

                elapsed_ms = int((time.monotonic() - start) * 1000)
                tokens = getattr(response, "tokens_used", 0) or 0

                node_trace = NodeTrace(
                    agent_name=node.agent_name,
                    duration_ms=elapsed_ms,
                    tokens_used=tokens,
                )

                # Fire POST_AGENT
                await self._fire(
                    HookEvent.POST_AGENT,
                    agent_name=node.agent_name,
                    cost_tokens=tokens,
                    node_trace=node_trace,
                    artifacts=self._store,
                )

                # Validate contract if present
                contract_passed: bool | None = None
                if node.contract:
                    contract_path = CONTRACT_DEF_DIR / f"{node.contract}.yaml"
                    if contract_path.exists():
                        contract = load_contract(contract_path)
                        html_artifact = self._store.get_optional("html", HtmlArtifact)
                        html = html_artifact.html if html_artifact else ""
                        result = await self._validator.validate(contract, html)
                        contract_passed = result.passed
                        if not result.passed:
                            logger.warning(
                                "pipeline.contract.failed",
                                extra={
                                    "run_id": run_id,
                                    "node": node_id,
                                    "contract": node.contract,
                                    "failures": [f.message for f in result.failures],
                                },
                            )
                            # Fire CONTRACT_FAILED
                            await self._fire(
                                HookEvent.CONTRACT_FAILED,
                                agent_name=node.agent_name,
                                metadata={
                                    "failures": [f.message for f in result.failures],
                                },
                                artifacts=self._store,
                            )
                            if self._settings.contract_strict:
                                raise PipelineExecutionError(
                                    f"Contract '{node.contract}' failed for node '{node_id}'"
                                )

                logger.info(
                    "pipeline.node.complete",
                    extra={
                        "run_id": run_id,
                        "node": node_id,
                        "duration_ms": elapsed_ms,
                        "contract_passed": contract_passed,
                    },
                )

                return NodeTrace(
                    agent_name=node.agent_name,
                    duration_ms=elapsed_ms,
                    tokens_used=tokens,
                    contract_passed=contract_passed,
                )

            except (PipelineExecutionError, HookAbortError):
                raise
            except Exception as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                return NodeTrace(
                    agent_name=node.agent_name,
                    duration_ms=elapsed_ms,
                    error=f"{type(exc).__name__}: {exc}",
                )

    def _merge_html_outputs(self, node_ids: list[str]) -> None:
        """Merge HTML-producing outputs from parallel nodes.

        Strategy: deterministic sequential merge in alphabetical agent order.
        Each agent's adapter writes to its own artifact name (e.g. dark_mode_html),
        so no conflict for the default full-build template. This method handles
        the edge case where multiple nodes write to the same artifact name.
        """
        if self._settings.merge_strategy != "sequential":
            return  # diff3 deferred to future phase

        # Check if multiple nodes produced artifacts with the same name.
        # In the current template design, each agent writes distinct artifact names,
        # so this is a safety net for custom templates.
        html_producers: list[str] = []
        for node_id in sorted(node_ids):  # alphabetical for determinism
            node = self._dag.nodes[node_id]
            if "html" in node.outputs and node_id != node_ids[0]:
                html_producers.append(node_id)

        if len(html_producers) > 1:
            logger.warning(
                "pipeline.merge.multiple_html_producers",
                extra={
                    "producers": html_producers,
                    "strategy": "last-writer-wins",
                },
            )

    async def _inject_proactive_warnings(self, run_id: str) -> None:
        """Query knowledge graph for proactive warnings and inject into artifact store."""
        try:
            from app.core.config import get_settings

            settings = get_settings()
            if not settings.knowledge.proactive_qa_enabled:
                return

            from app.knowledge.proactive_qa import ProactiveWarningInjector

            injector = ProactiveWarningInjector(settings)

            # Extract component slugs from build plan artifact if available
            plan = self._store.get_optional("plan", BuildPlanArtifact)
            component_slugs = _extract_component_slugs(plan) if plan else []

            # Extract client IDs from store metadata
            client_ids = _extract_client_ids(self._store)

            if not component_slugs and not client_ids:
                return

            warnings = await injector.query_warnings(
                component_slugs=component_slugs,
                client_ids=client_ids,
                project_id=None,
            )

            if warnings:
                artifact = ProactiveWarningsArtifact(
                    name="proactive_warnings",
                    produced_by="proactive_qa",
                    produced_at=datetime.now(UTC),
                    warnings=tuple(warnings),
                    formatted_text=injector.format_warnings_for_prompt(warnings),
                )
                self._store.put("proactive_warnings", artifact)
                logger.info(
                    "pipeline.proactive_warnings.injected",
                    extra={"run_id": run_id, "count": len(warnings)},
                )
        except Exception:
            logger.warning("pipeline.proactive_warnings.failed", exc_info=True)


def _extract_component_slugs(plan: BuildPlanArtifact | None) -> list[str]:
    """Extract component slugs from a build plan artifact."""
    if plan is None or plan.plan is None:
        return []
    slugs: list[str] = []
    for section in getattr(plan.plan, "sections", []):
        slug = getattr(section, "component_slug", None)
        if slug:
            slugs.append(slug)
    return slugs


def _extract_client_ids(store: ArtifactStore) -> list[str]:  # noqa: ARG001
    """Extract client IDs from artifact store metadata."""
    # Client IDs may be stored in a design tokens artifact or similar
    # For now, return empty — adapters will populate as needed
    return []
