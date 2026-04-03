# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Credential pool health endpoint — admin-only visibility into key rotation state."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.credentials import get_all_pools
from app.core.logging import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/credentials", tags=["credentials"])


class KeyHealthReport(BaseModel):
    key_hash: str
    status: str  # "healthy" | "cooled_down" | "unhealthy"
    failure_count: int
    last_failure_code: int | None
    cooldown_remaining_s: float


class ServiceHealthReport(BaseModel):
    service: str
    key_count: int
    healthy: int
    cooled_down: int
    unhealthy: int
    keys: list[KeyHealthReport]


class CredentialHealthResponse(BaseModel):
    services: list[ServiceHealthReport]
    total_keys: int
    healthy_total: int
    cooled_down_total: int
    unhealthy_total: int


@router.get("/health", response_model=CredentialHealthResponse)
@limiter.limit("60/minute")
async def credential_health(
    request: Request,  # noqa: ARG001 — required by limiter
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> CredentialHealthResponse:
    """Return health status for all credential pools. Admin-only."""
    pools = get_all_pools()
    services: list[ServiceHealthReport] = []
    total = healthy = cooled = unhealthy = 0

    for _name, pool in sorted(pools.items()):
        status = await pool.pool_status()
        report = ServiceHealthReport(**status)
        services.append(report)
        total += report.key_count
        healthy += report.healthy
        cooled += report.cooled_down
        unhealthy += report.unhealthy

    logger.info("credentials.health_checked", total_keys=total, services=len(services))
    return CredentialHealthResponse(
        services=services,
        total_keys=total,
        healthy_total=healthy,
        cooled_down_total=cooled,
        unhealthy_total=unhealthy,
    )
