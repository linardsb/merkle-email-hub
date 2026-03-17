"""Versioned prompt template store for agent system prompts.

Stores agent prompts in the database with version history, A/B variant support,
and rollback capability. Falls back to SKILL.md when disabled or empty.
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── SQLAlchemy Model ──


class PromptTemplate(Base):
    """A versioned agent prompt template."""

    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    variant: Mapped[str] = mapped_column(sa.String(64), nullable=False, server_default="default")
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    created_by: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        sa.Index("ix_prompt_templates_agent_variant", "agent_id", "variant"),
        sa.Index("ix_prompt_templates_active", "agent_id", "variant", "active"),
    )


# ── Repository ──


class PromptTemplateRepository:
    """CRUD for prompt templates."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_active(self, agent_id: str, variant: str = "default") -> PromptTemplate | None:
        """Fetch the active prompt for an agent+variant."""
        result = await self._db.execute(
            select(PromptTemplate).where(
                PromptTemplate.agent_id == agent_id,
                PromptTemplate.variant == variant,
                PromptTemplate.active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, template_id: int) -> PromptTemplate | None:
        """Fetch a prompt template by ID."""
        result = await self._db.execute(
            select(PromptTemplate).where(PromptTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self, agent_id: str, variant: str = "default", limit: int = 20
    ) -> list[PromptTemplate]:
        """List versions for an agent+variant, ordered by version desc."""
        result = await self._db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.agent_id == agent_id, PromptTemplate.variant == variant)
            .order_by(PromptTemplate.version.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_agents(self) -> list[str]:
        """List distinct agent IDs that have prompt templates."""
        result = await self._db.execute(
            select(PromptTemplate.agent_id).distinct().order_by(PromptTemplate.agent_id)
        )
        return list(result.scalars().all())

    async def create(
        self,
        agent_id: str,
        variant: str,
        content: str,
        description: str | None = None,
        created_by: str | None = None,
    ) -> PromptTemplate:
        """Create a new prompt version. Auto-increments version per agent+variant."""
        # Get next version number
        result = await self._db.execute(
            select(func.coalesce(func.max(PromptTemplate.version), 0)).where(
                PromptTemplate.agent_id == agent_id,
                PromptTemplate.variant == variant,
            )
        )
        next_version: int = result.scalar_one() + 1

        template = PromptTemplate(
            agent_id=agent_id,
            variant=variant,
            version=next_version,
            content=content,
            description=description,
            active=False,
            created_by=created_by,
        )
        self._db.add(template)
        await self._db.flush()
        return template

    async def activate(self, template_id: int) -> PromptTemplate | None:
        """Activate a specific version, deactivating all others for same agent+variant."""
        template = await self.get_by_id(template_id)
        if template is None:
            return None

        # Deactivate all versions for this agent+variant
        await self._db.execute(
            sa.update(PromptTemplate)
            .where(
                PromptTemplate.agent_id == template.agent_id,
                PromptTemplate.variant == template.variant,
            )
            .values(active=False)
        )

        # Activate the target version
        template.active = True
        await self._db.flush()
        return template

    async def rollback(self, agent_id: str, variant: str = "default") -> PromptTemplate | None:
        """Activate the previous version (N-1). Returns None if no previous exists."""
        active = await self.get_active(agent_id, variant)
        if active is None or active.version <= 1:
            return None

        # Find the previous version
        result = await self._db.execute(
            select(PromptTemplate).where(
                PromptTemplate.agent_id == agent_id,
                PromptTemplate.variant == variant,
                PromptTemplate.version == active.version - 1,
            )
        )
        previous = result.scalar_one_or_none()
        if previous is None:
            return None

        return await self.activate(previous.id)


# ── Service ──


class PromptStoreService:
    """Business logic for prompt template operations."""

    async def get_prompt(
        self, db: AsyncSession, agent_id: str, variant: str = "default"
    ) -> str | None:
        """Get the active prompt content for an agent. Returns None if not found."""
        repo = PromptTemplateRepository(db)
        template = await repo.get_active(agent_id, variant)
        return template.content if template else None

    async def seed_from_skill_files(self, db: AsyncSession) -> dict[str, int]:
        """Seed prompt store from SKILL.md files for agents without DB entries.

        Returns mapping of agent_id -> version for seeded agents.
        """
        from app.ai.agents.skills_routes import AGENT_NAMES, AGENTS_DIR

        repo = PromptTemplateRepository(db)
        existing_agents = set(await repo.list_agents())
        seeded: dict[str, int] = {}

        for agent_name in AGENT_NAMES:
            if agent_name in existing_agents:
                logger.info(
                    "prompt_store.seed_skipped", agent_id=agent_name, reason="already_exists"
                )
                continue

            skill_path = AGENTS_DIR / agent_name / "SKILL.md"
            if not skill_path.exists():
                logger.warning(
                    "prompt_store.seed_skipped", agent_id=agent_name, reason="no_skill_file"
                )
                continue

            content = skill_path.read_text(encoding="utf-8")
            template = await repo.create(
                agent_id=agent_name,
                variant="default",
                content=content,
                description="Seeded from SKILL.md",
            )
            await repo.activate(template.id)
            seeded[agent_name] = template.version
            logger.info(
                "prompt_store.seed_completed",
                agent_id=agent_name,
                version=template.version,
            )

        await db.commit()
        return seeded


# ── Cache pre-loading ──


async def preload_prompt_store_cache(db: AsyncSession) -> None:
    """Load all active prompt templates into the skill_override cache.

    Called at startup and after any prompt mutation (create/activate/rollback).
    """
    settings = get_settings()
    if not settings.ai.prompt_store_enabled:
        return

    from app.ai.agents.skill_override import clear_store_cache, set_store_cache

    clear_store_cache()
    repo = PromptTemplateRepository(db)
    agents = await repo.list_agents()
    for agent_id in agents:
        template = await repo.get_active(agent_id)
        if template:
            set_store_cache(agent_id, template.content)
            logger.info(
                "prompt_store.cache_loaded",
                agent_id=agent_id,
                version=template.version,
                variant=template.variant,
            )
