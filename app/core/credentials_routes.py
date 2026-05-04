# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Credential pool health endpoint — admin-only visibility into key rotation state."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.credentials import (
    get_all_pools,
    is_revoked,
    restore_for_agent,
    revoke_for_agent,
)
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


class RevokeRequest(BaseModel):
    agent_id: str
    reason: str = "manual_admin_revocation"
    ttl_s: int | None = None
    restore: bool = False


class RevokeResponse(BaseModel):
    agent_id: str
    revoked: bool
    restored: bool


@router.post("/revoke", response_model=RevokeResponse)
@limiter.limit("30/minute")
async def revoke_agent_credentials(
    request: Request,  # noqa: ARG001 — required by limiter
    payload: RevokeRequest,
    current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> RevokeResponse:
    """Revoke (or restore) an agent's credential leases. Admin-only (51.1).

    Setting ``restore=true`` lifts an existing revocation. Otherwise a new
    revocation is recorded with the supplied reason and optional TTL; if
    ``ttl_s`` is omitted, ``settings.security.revocation_default_ttl_s``
    applies (``None`` = permanent until restored).
    """
    if payload.restore:
        was_revoked = await restore_for_agent(payload.agent_id)
        logger.info(
            "credentials.restore_requested",
            user_id=current_user.id,
            user_email=current_user.email,
            agent_id=payload.agent_id,
            was_revoked=was_revoked,
        )
        return RevokeResponse(agent_id=payload.agent_id, revoked=False, restored=was_revoked)

    await revoke_for_agent(payload.agent_id, payload.reason, ttl=payload.ttl_s)
    revoked = await is_revoked(payload.agent_id)
    logger.info(
        "credentials.revoke_requested",
        user_id=current_user.id,
        user_email=current_user.email,
        agent_id=payload.agent_id,
        reason=payload.reason,
        ttl_s=payload.ttl_s,
    )
    return RevokeResponse(agent_id=payload.agent_id, revoked=revoked, restored=False)


@router.get("/health", response_model=CredentialHealthResponse)
@limiter.limit("60/minute")
async def credential_health(
    request: Request,  # noqa: ARG001 — required by limiter
    current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> JSONResponse:
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

    logger.info(
        "credentials.health_checked",
        user_id=current_user.id,
        user_email=current_user.email,
        total_keys=total,
        services=len(services),
    )
    response_data = CredentialHealthResponse(
        services=services,
        total_keys=total,
        healthy_total=healthy,
        cooled_down_total=cooled,
        unhealthy_total=unhealthy,
    )
    return JSONResponse(
        content=response_data.model_dump(),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )
