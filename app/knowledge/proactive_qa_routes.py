# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Proactive QA warning preview and failure graph API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.requests import Request
from pydantic import BaseModel

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.rate_limit import limiter

router = APIRouter(tags=["knowledge"])


# ── Response Schemas ──


class ProactiveWarningResponse(BaseModel):
    component: str
    client: str
    failure: str
    severity: str
    suggestion: str
    occurrence_count: int


class ProactiveWarningsResponse(BaseModel):
    warnings: list[ProactiveWarningResponse]
    component_count: int
    client_count: int


class FailureEdge(BaseModel):
    client: str
    failure_type: str
    severity: str
    occurrence_count: int
    first_seen: str
    last_seen: str


class FailureGraphResponse(BaseModel):
    component: str
    edges: list[FailureEdge]


# ── Endpoints ──


@router.get("/proactive-warnings", response_model=ProactiveWarningsResponse)
@limiter.limit("30/minute")
async def get_proactive_warnings(
    request: Request,
    components: str = Query(
        ...,
        description="Comma-separated component slugs",
        max_length=500,
    ),
    clients: str = Query(
        ...,
        description="Comma-separated email client IDs",
        max_length=500,
    ),
    user: User = Depends(require_role("admin", "developer")),  # noqa: B008
) -> ProactiveWarningsResponse:
    """Preview proactive QA warnings for given components and clients."""
    _ = request, user

    from app.core.config import get_settings
    from app.knowledge.proactive_qa import ProactiveWarningInjector

    settings = get_settings()
    component_slugs = [s.strip() for s in components.split(",") if s.strip()]
    client_ids = [s.strip() for s in clients.split(",") if s.strip()]

    injector = ProactiveWarningInjector(settings)
    warnings = await injector.query_warnings(
        component_slugs=component_slugs,
        client_ids=client_ids,
        project_id=None,
    )

    return ProactiveWarningsResponse(
        warnings=[
            ProactiveWarningResponse(
                component=w.component,
                client=w.client,
                failure=w.failure,
                severity=w.severity,
                suggestion=w.suggestion,
                occurrence_count=w.occurrence_count,
            )
            for w in warnings
        ],
        component_count=len({w.component for w in warnings}),
        client_count=len({w.client for w in warnings}),
    )


@router.get("/failure-graph", response_model=FailureGraphResponse)
@limiter.limit("30/minute")
async def get_failure_graph(
    request: Request,
    component: str = Query(
        ...,
        description="Component slug",
        max_length=100,
    ),
    user: User = Depends(require_role("admin", "developer")),  # noqa: B008
) -> FailureGraphResponse:
    """Get failure graph edges for a component."""
    _ = request, user

    from app.core.config import get_settings
    from app.knowledge.proactive_qa import ProactiveWarningInjector

    settings = get_settings()
    injector = ProactiveWarningInjector(settings)

    # Query with just the component, no client filter
    warnings = await injector.query_warnings(
        component_slugs=[component],
        client_ids=[],
        project_id=None,
    )

    return FailureGraphResponse(
        component=component,
        edges=[
            FailureEdge(
                client=w.client,
                failure_type=w.failure,
                severity=w.severity,
                occurrence_count=w.occurrence_count,
                first_seen=w.first_seen,
                last_seen=w.last_seen,
            )
            for w in warnings
        ],
    )
