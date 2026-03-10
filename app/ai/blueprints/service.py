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
        graph_provider: GraphContextProvider | None = None
        try:
            from app.core.config import get_settings

            settings = get_settings()
            if settings.cognee.enabled:
                from app.knowledge.graph.cognee_provider import CogneeGraphProvider

                graph_provider = CogneeGraphProvider(settings)
        except Exception:
            logger.debug("blueprint.graph_provider_init_skipped", exc_info=True)

        engine = BlueprintEngine(
            definition,
            component_resolver=component_resolver,
            on_handoff=persist_handoff_to_memory,
            project_id=project_id,
            graph_provider=graph_provider,
            audience_profile=audience_profile,
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
                persist_outcome_to_memory,
                queue_outcome_for_graph,
            )

            await queue_outcome_for_graph(bp_run, definition.name, project_id)
            await persist_outcome_to_memory(bp_run, definition.name, project_id)
        except Exception:
            logger.warning(
                "blueprint.outcome_logging_failed",
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
        )


_service: BlueprintService | None = None


def get_blueprint_service() -> BlueprintService:
    """Module-level singleton for the blueprint service."""
    global _service
    if _service is None:
        _service = BlueprintService()
    return _service
