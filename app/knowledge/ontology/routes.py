"""Ontology REST endpoints — competitive intelligence reports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.knowledge.ontology.schemas import (
    CapabilityFeasibilityResponse,
    CompetitiveReportResponse,
    CompetitiveReportTextResponse,
    EmailClientResponse,
)

if TYPE_CHECKING:
    from app.knowledge.ontology.competitive_feasibility import CapabilityFeasibility

router = APIRouter(prefix="/api/v1/ontology", tags=["ontology"])


@router.get("/clients", response_model=list[EmailClientResponse])
@limiter.limit("30/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def list_email_clients(
    request: Request,  # noqa: ARG001
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
) -> list[EmailClientResponse]:
    """List all email clients from the ontology registry."""
    from app.knowledge.ontology.registry import load_ontology

    registry = load_ontology()
    return [
        EmailClientResponse(
            id=c.id,
            name=c.name,
            family=c.family,
            platform=c.platform,
            engine=c.engine.value,
            market_share=c.market_share,
        )
        for c in registry.clients
    ]


def _to_response(f: CapabilityFeasibility) -> CapabilityFeasibilityResponse:
    return CapabilityFeasibilityResponse(
        id=f.capability_id,
        name=f.capability_name,
        category=f.category,
        audience_coverage=round(f.audience_coverage, 2),
        blocking_clients=list(f.blocking_clients),
        hub_supports=f.hub_supports,
        hub_agent=f.hub_agent,
        competitor_names=list(f.competitor_names),
    )


@router.get("/competitive-report", response_model=CompetitiveReportResponse)
@limiter.limit("10/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def get_competitive_report(
    request: Request,  # noqa: ARG001
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    client_ids: Annotated[list[str], Query()] = [],  # noqa: B006
    competitor_id: Annotated[str | None, Query()] = None,
) -> CompetitiveReportResponse:
    """Get audience-scoped competitive feasibility report.

    Query params:
        client_ids: Target audience email client IDs (repeatable)
        competitor_id: Optional — focus on single competitor
    """
    from app.knowledge.ontology.competitive_feasibility import build_competitive_report

    report = build_competitive_report(
        client_ids=tuple(client_ids),
        competitor_id=competitor_id,
    )

    return CompetitiveReportResponse(
        audience_client_ids=list(report.audience_client_ids),
        total_capabilities=len(report.feasibilities),
        hub_advantages=[_to_response(f) for f in report.hub_advantages],
        gaps=[_to_response(f) for f in report.gaps],
        opportunities=[_to_response(f) for f in report.opportunities],
        full_matrix=[_to_response(f) for f in report.feasibilities],
    )


@router.get("/competitive-report/text", response_model=CompetitiveReportTextResponse)
@limiter.limit("10/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def get_competitive_report_text(
    request: Request,  # noqa: ARG001
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
) -> CompetitiveReportTextResponse:
    """Get full competitive landscape report as formatted text."""
    from app.ai.blueprints.competitor_context import format_full_competitive_report

    return CompetitiveReportTextResponse(report=format_full_competitive_report())
