"""Ontology REST endpoints — competitive intelligence reports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.knowledge.ontology.schemas import (
    CapabilityFeasibilityResponse,
    ChangelogEntryResponse,
    CompetitiveReportResponse,
    CompetitiveReportTextResponse,
    EmailClientResponse,
    SyncReportResponse,
    SyncStatusResponse,
)

if TYPE_CHECKING:
    from app.knowledge.ontology.competitive_feasibility import CapabilityFeasibility

router = APIRouter(prefix="/api/v1/ontology", tags=["ontology"])


@router.get("/clients", response_model=list[EmailClientResponse])
@limiter.limit("30/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def list_email_clients(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
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
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
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
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CompetitiveReportTextResponse:
    """Get full competitive landscape report as formatted text."""
    from app.ai.blueprints.competitor_context import format_full_competitive_report

    return CompetitiveReportTextResponse(report=format_full_competitive_report())


@router.post("/sync", response_model=SyncReportResponse)
@limiter.limit("2/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def trigger_sync(
    request: Request,
    _current_user: User = Depends(require_role("admin")),
    dry_run: bool = True,
) -> SyncReportResponse:
    """Manually trigger a Can I Email ontology sync.

    Admin only. Defaults to dry_run=True for safety.
    """
    from app.core.exceptions import ForbiddenError
    from app.knowledge.ontology.sync.service import CanIEmailSyncService

    settings = get_settings()
    if not settings.ontology_sync.enabled:
        raise ForbiddenError("Ontology sync is disabled")

    service = CanIEmailSyncService()
    report = await service.sync(dry_run=dry_run)

    return SyncReportResponse(
        new_properties=report.new_properties,
        updated_levels=report.updated_levels,
        new_clients=report.new_clients,
        changelog=[
            ChangelogEntryResponse(
                property_id=c.property_id,
                client_id=c.client_id,
                old_level=c.old_level,
                new_level=c.new_level,
                source=c.source,
            )
            for c in report.changelog
        ],
        errors=report.errors,
        dry_run=report.dry_run,
        commit_sha=report.commit_sha,
    )


@router.get("/sync-status", response_model=SyncStatusResponse)
@limiter.limit("30/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def get_sync_status(
    request: Request,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SyncStatusResponse:
    """Get the last sync status and report."""
    from app.knowledge.ontology.sync.service import CanIEmailSyncService

    service = CanIEmailSyncService()
    status = await service.get_status()

    return SyncStatusResponse(
        last_sync_at=status.last_sync_at,
        last_commit_sha=status.last_commit_sha,
        features_synced=status.features_synced,
        error_count=status.error_count,
        last_report=status.last_report,
    )
