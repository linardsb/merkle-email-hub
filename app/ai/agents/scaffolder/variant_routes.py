"""Multi-variant campaign assembly API routes."""

# pyright: reportUntypedFunctionDecorator=false, reportUnknownMemberType=false

from fastapi import APIRouter, Depends, Request

from app.ai.agents.scaffolder.schemas import VariantRequest, VariantSetResponse
from app.ai.agents.scaffolder.service import ScaffolderService, get_scaffolder_service
from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.logging import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/agents/scaffolder", tags=["agents"])


@router.post("/generate-variants", response_model=VariantSetResponse)
@limiter.limit("3/hour")
async def generate_variants(
    request: Request,  # noqa: ARG001 — required by @limiter.limit
    body: VariantRequest,
    service: ScaffolderService = Depends(get_scaffolder_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
) -> VariantSetResponse:
    """Generate A/B/n email variants from a single campaign brief.

    Produces 2-5 variants, each with a distinct content strategy,
    shared template and design tokens, independent QA results,
    and a comparison matrix showing measurable differences.
    """
    return await service.generate_variants(body)
