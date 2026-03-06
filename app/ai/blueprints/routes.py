# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Blueprint API routes — synchronous run endpoint for v1."""

from fastapi import APIRouter, Depends, Request

from app.ai.blueprints.schemas import BlueprintRunRequest, BlueprintRunResponse
from app.ai.blueprints.service import get_blueprint_service
from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])


@router.post(
    "/run",
    response_model=BlueprintRunResponse,
    dependencies=[Depends(require_role("admin", "developer"))],
)
@limiter.limit("3/minute")
async def run_blueprint(
    request: Request,  # noqa: ARG001 — required by slowapi @limiter.limit
    body: BlueprintRunRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> BlueprintRunResponse:
    """Execute a named blueprint and return the full run result.

    Synchronous for v1 — progress is included in the response body.
    """
    service = get_blueprint_service()
    return await service.run(body, user_id=current_user.id)
