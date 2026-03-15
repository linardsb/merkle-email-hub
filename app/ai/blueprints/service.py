"""Blueprint service — resolves and executes named blueprints."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.blueprints.definitions.campaign import build_campaign_blueprint
from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
from app.ai.blueprints.exceptions import BlueprintError
from app.ai.blueprints.protocols import AgentHandoff, ComponentResolver, GraphContextProvider
from app.ai.blueprints.schemas import (
    BlueprintProgress,
    BlueprintRunRequest,
    BlueprintRunResponse,
    HandoffSummary,
    InlineJudgeCriterionResponse,
    InlineJudgeVerdictResponse,
    RoutingDecisionResponse,
)
from app.core.logging import get_logger
from app.personas.schemas import PersonaResponse

logger = get_logger(__name__)

BLUEPRINT_REGISTRY: dict[str, Callable[[], BlueprintDefinition]] = {
    "campaign": build_campaign_blueprint,
}


class BlueprintService:
    """Resolves blueprint by name and runs the engine."""

    async def run(
        self,
        request: BlueprintRunRequest,
        user_id: int | None = None,
        db: AsyncSession | None = None,
    ) -> BlueprintRunResponse:
        """Execute a named blueprint and return structured response."""
        factory = BLUEPRINT_REGISTRY.get(request.blueprint_name)
        if factory is None:
            available = ", ".join(sorted(BLUEPRINT_REGISTRY.keys()))
            raise BlueprintError(
                f"Unknown blueprint '{request.blueprint_name}'. Available: {available}"
            )

        definition = factory()

        component_resolver: ComponentResolver | None = None
        if db is not None:
            from app.ai.blueprints.resolvers import DbComponentResolver

            component_resolver = DbComponentResolver(db)

        # Wire handoff → memory persistence callback
        from app.ai.blueprints.handoff_memory import persist_handoff_to_memory

        raw_project_id = request.options.get("project_id") if request.options else None
        project_id: int | None = int(str(raw_project_id)) if raw_project_id is not None else None

        # Resolve target audience personas
        from app.ai.blueprints.audience_context import (
            AudienceProfile,
            build_audience_profile,
            format_audience_context,
        )

        audience_profile: AudienceProfile | None = None
        if request.persona_ids and db is not None:
            from app.personas.service import PersonaService

            persona_svc = PersonaService(db)
            personas: list[PersonaResponse] = []
            for pid in request.persona_ids:
                try:
                    personas.append(await persona_svc.get_persona(pid))
                except Exception:
                    logger.warning("blueprint.persona_not_found", persona_id=pid, exc_info=True)
            if personas:
                audience_profile = build_audience_profile(personas)

        # Wire graph knowledge provider (optional — only if Cognee enabled)
        from app.core.config import get_settings

        settings = get_settings()
        graph_provider: GraphContextProvider | None = None
        try:
            if settings.cognee.enabled:
                from app.knowledge.graph.cognee_provider import CogneeGraphProvider

                graph_provider = CogneeGraphProvider(settings)
        except Exception:
            logger.debug("blueprint.graph_provider_init_skipped", exc_info=True)

        # Load design system from project (single DB read)
        from app.projects.design_system import DesignSystem, load_design_system

        design_system: DesignSystem | None = None
        if project_id is not None and db is not None:
            try:
                from app.projects.repository import ProjectRepository

                repo = ProjectRepository(db)
                project = await repo.get(project_id)
                if project is not None:
                    design_system = load_design_system(project.design_system)
            except Exception:
                logger.warning(
                    "blueprint.design_system_load_failed",
                    project_id=project_id,
                    exc_info=True,
                )

        engine = BlueprintEngine(
            definition,
            component_resolver=component_resolver,
            on_handoff=persist_handoff_to_memory,
            project_id=project_id,
            graph_provider=graph_provider,
            audience_profile=audience_profile,
            judge_on_retry=settings.blueprint.judge_on_retry,
            design_system=design_system,
        )

        logger.info(
            "blueprint.service.run_started",
            blueprint=request.blueprint_name,
        )

        bp_run = await engine.run(
            brief=request.brief,
            initial_html=request.initial_html,
            user_id=user_id,
        )

        # Post-run: log outcome to graph queue + memory (fire-and-forget)
        try:
            from app.ai.blueprints.outcome_logger import (
                extract_and_store_failure_patterns,
                persist_outcome_to_memory,
                queue_outcome_for_graph,
            )

            await queue_outcome_for_graph(bp_run, definition.name, project_id)
            await persist_outcome_to_memory(bp_run, definition.name, project_id)
            await extract_and_store_failure_patterns(
                bp_run, definition.name, project_id, audience_profile
            )
        except Exception:
            logger.warning(
                "blueprint.outcome_logging_failed",
                run_id=bp_run.run_id,
                exc_info=True,
            )

        # Post-run: enqueue for production judge sampling (fire-and-forget)
        if bp_run.status == "completed" and bp_run.qa_passed:
            try:
                from app.ai.agents.evals.production_sampler import enqueue_for_judging

                agents_executed = [p.node_name for p in bp_run.progress if p.node_type == "agentic"]
                await enqueue_for_judging(
                    run_id=bp_run.run_id,
                    blueprint_name=definition.name,
                    brief=request.brief,
                    html=bp_run.html,
                    agents_executed=agents_executed,
                )
            except Exception:
                logger.warning(
                    "blueprint.production_sampling_failed",
                    run_id=bp_run.run_id,
                    exc_info=True,
                )

        def _to_summary(h: AgentHandoff) -> HandoffSummary:
            return HandoffSummary(
                agent_name=h.agent_name,
                decisions=list(h.decisions),
                warnings=list(h.warnings),
                component_refs=list(h.component_refs),
                confidence=h.confidence,
            )

        final_handoff: HandoffSummary | None = None
        if bp_run._last_handoff is not None:
            final_handoff = _to_summary(bp_run._last_handoff)

        handoff_history = [_to_summary(h) for h in bp_run._handoff_history]

        # Map inline judge verdict to response
        judge_verdict_response: InlineJudgeVerdictResponse | None = None
        if bp_run.judge_verdict is not None:
            judge_verdict_response = InlineJudgeVerdictResponse(
                trace_id=bp_run.judge_verdict.trace_id,
                agent=bp_run.judge_verdict.agent,
                overall_pass=bp_run.judge_verdict.overall_pass,
                criteria_results=[
                    InlineJudgeCriterionResponse(
                        criterion=cr.criterion,
                        passed=cr.passed,
                        reasoning=cr.reasoning,
                    )
                    for cr in bp_run.judge_verdict.criteria_results
                ],
            )

        return BlueprintRunResponse(
            run_id=bp_run.run_id,
            blueprint_name=definition.name,
            status=bp_run.status,
            html=bp_run.html,
            progress=[
                BlueprintProgress(
                    node_name=p.node_name,
                    node_type=p.node_type,
                    status=p.status,
                    iteration=p.iteration,
                    summary=p.summary,
                    duration_ms=p.duration_ms,
                )
                for p in bp_run.progress
            ],
            qa_passed=bp_run.qa_passed,
            model_usage=bp_run.model_usage,
            final_handoff=final_handoff,
            handoff_history=handoff_history,
            audience_summary=(
                format_audience_context(audience_profile) if audience_profile else None
            ),
            skipped_nodes=bp_run.skipped_nodes,
            routing_decisions=[
                RoutingDecisionResponse(
                    node_name=d.node_name,
                    action=d.action.value,
                    reason=d.reason,
                )
                for d in bp_run.routing_decisions
            ],
            judge_verdict=judge_verdict_response,
        )


_service: BlueprintService | None = None


def get_blueprint_service() -> BlueprintService:
    """Module-level singleton for the blueprint service."""
    global _service
    if _service is None:
        _service = BlueprintService()
    return _service
