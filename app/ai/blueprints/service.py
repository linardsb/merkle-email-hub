"""Blueprint service — resolves and executes named blueprints."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.blueprints.definitions.campaign import build_campaign_blueprint
from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
from app.ai.blueprints.exceptions import BlueprintError
from app.ai.blueprints.protocols import ComponentResolver
from app.ai.blueprints.schemas import (
    BlueprintProgress,
    BlueprintRunRequest,
    BlueprintRunResponse,
    HandoffSummary,
)
from app.core.logging import get_logger

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

        engine = BlueprintEngine(definition, component_resolver=component_resolver)

        logger.info(
            "blueprint.service.run_started",
            blueprint=request.blueprint_name,
        )

        bp_run = await engine.run(
            brief=request.brief,
            initial_html=request.initial_html,
            user_id=user_id,
        )

        final_handoff: HandoffSummary | None = None
        if bp_run._last_handoff is not None:
            h = bp_run._last_handoff
            final_handoff = HandoffSummary(
                agent_name=h.agent_name,
                decisions=list(h.decisions),
                warnings=list(h.warnings),
                component_refs=list(h.component_refs),
                confidence=h.confidence,
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
        )


_service: BlueprintService | None = None


def get_blueprint_service() -> BlueprintService:
    """Module-level singleton for the blueprint service."""
    global _service
    if _service is None:
        _service = BlueprintService()
    return _service
