"""REST API routes for the versioned prompt template store."""

# pyright: reportUntypedFunctionDecorator=false, reportUnknownMemberType=false

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.skills_routes import AGENT_NAMES
from app.ai.prompt_store import (
    PromptStoreService,
    PromptTemplateRepository,
    preload_prompt_store_cache,
)
from app.ai.prompt_store_schemas import (
    PromptActivateRequest,
    PromptSeedResponse,
    PromptTemplateCreate,
    PromptTemplateListResponse,
    PromptTemplateResponse,
)
from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.core.scoped_db import get_scoped_db

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])

_service = PromptStoreService()


def _validate_agent_id(agent_id: str) -> None:
    """Raise NotFoundError for unknown agent IDs."""
    if agent_id not in AGENT_NAMES:
        raise NotFoundError(f"Unknown agent: {agent_id}")


@router.get("")
@limiter.limit("30/minute")
async def list_agents(
    request: Request,
    db: AsyncSession = Depends(get_scoped_db),  # noqa: B008
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> dict[str, list[str]]:
    """List all agents with prompt store entries."""
    _ = request
    repo = PromptTemplateRepository(db)
    agents = await repo.list_agents()
    return {"agents": agents}


@router.get("/{agent_id}")
@limiter.limit("30/minute")
async def get_active_prompt(
    request: Request,
    agent_id: str,
    variant: str = "default",
    db: AsyncSession = Depends(get_scoped_db),  # noqa: B008
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> PromptTemplateResponse:
    """Get the active prompt for an agent+variant."""
    _ = request
    _validate_agent_id(agent_id)
    repo = PromptTemplateRepository(db)
    template = await repo.get_active(agent_id, variant)
    if template is None:
        raise NotFoundError(f"No active prompt for agent {agent_id} variant {variant}")
    return PromptTemplateResponse.model_validate(template)


@router.get("/{agent_id}/versions")
@limiter.limit("30/minute")
async def list_versions(
    request: Request,
    agent_id: str,
    variant: str = "default",
    limit: int = 20,
    db: AsyncSession = Depends(get_scoped_db),  # noqa: B008
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> PromptTemplateListResponse:
    """List version history for an agent+variant."""
    _ = request
    _validate_agent_id(agent_id)
    capped_limit = min(limit, 100)
    repo = PromptTemplateRepository(db)
    templates = await repo.list_versions(agent_id, variant, capped_limit)
    return PromptTemplateListResponse(
        templates=[PromptTemplateResponse.model_validate(t) for t in templates]
    )


@router.post("", status_code=201)
@limiter.limit("10/minute")
async def create_prompt(
    request: Request,
    body: PromptTemplateCreate,
    db: AsyncSession = Depends(get_scoped_db),  # noqa: B008
    current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> PromptTemplateResponse:
    """Create a new prompt version for an agent."""
    _ = request
    _validate_agent_id(body.agent_id)
    repo = PromptTemplateRepository(db)
    template = await repo.create(
        agent_id=body.agent_id,
        variant=body.variant,
        content=body.content,
        description=body.description,
        created_by=current_user.email,
    )
    await db.commit()
    await preload_prompt_store_cache(db)
    logger.info(
        "prompt_store.create_completed",
        agent_id=body.agent_id,
        variant=body.variant,
        version=template.version,
    )
    return PromptTemplateResponse.model_validate(template)


@router.post("/activate")
@limiter.limit("10/minute")
async def activate_prompt(
    request: Request,
    body: PromptActivateRequest,
    db: AsyncSession = Depends(get_scoped_db),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> PromptTemplateResponse:
    """Activate a specific prompt version."""
    _ = request
    repo = PromptTemplateRepository(db)
    template = await repo.activate(body.template_id)
    if template is None:
        raise NotFoundError(f"Prompt template {body.template_id} not found")
    await db.commit()
    await preload_prompt_store_cache(db)
    logger.info(
        "prompt_store.activate_completed",
        template_id=body.template_id,
        agent_id=template.agent_id,
        version=template.version,
    )
    return PromptTemplateResponse.model_validate(template)


@router.post("/{agent_id}/rollback")
@limiter.limit("5/minute")
async def rollback_prompt(
    request: Request,
    agent_id: str,
    variant: str = "default",
    db: AsyncSession = Depends(get_scoped_db),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> PromptTemplateResponse:
    """Rollback to the previous prompt version."""
    _ = request
    _validate_agent_id(agent_id)
    repo = PromptTemplateRepository(db)
    template = await repo.rollback(agent_id, variant)
    if template is None:
        raise NotFoundError(f"No previous version to rollback to for {agent_id}")
    await db.commit()
    await preload_prompt_store_cache(db)
    logger.info(
        "prompt_store.rollback_completed",
        agent_id=agent_id,
        variant=variant,
        version=template.version,
    )
    return PromptTemplateResponse.model_validate(template)


@router.post("/seed")
@limiter.limit("2/minute")
async def seed_prompts(
    request: Request,
    db: AsyncSession = Depends(get_scoped_db),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> PromptSeedResponse:
    """Seed prompt store from SKILL.md files."""
    _ = request
    seeded = await _service.seed_from_skill_files(db)
    await preload_prompt_store_cache(db)
    logger.info("prompt_store.seed_completed", seeded_count=len(seeded))
    return PromptSeedResponse(seeded=seeded)
