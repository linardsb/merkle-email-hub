"""Adaptive model tier routing — tracks per-agent per-project success rates.

When enabled (AI__ADAPTIVE_ROUTING_ENABLED=true), monitors acceptance rates
and auto-adjusts model tier: downgrades when a lower tier performs well,
upgrades when the current tier underperforms.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.ai.routing import TaskTier
from app.core.database import Base
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── SQLAlchemy Model ──


class RoutingHistoryEntry(Base):
    """Records the tier used and outcome for each agent invocation."""

    __tablename__ = "routing_history"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, index=True)
    tier_used: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    accepted: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (sa.Index("ix_routing_history_agent_project", "agent_name", "project_id"),)


# ── Repository ──


class RoutingHistoryRepository:
    """CRUD for routing history entries."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        agent_name: str,
        project_id: int | None,
        tier_used: TaskTier,
        accepted: bool,
    ) -> None:
        """Record a routing outcome (fire-and-forget safe)."""
        entry = RoutingHistoryEntry(
            agent_name=agent_name,
            project_id=project_id,
            tier_used=tier_used,
            accepted=accepted,
        )
        self._db.add(entry)

    async def get_acceptance_rate(
        self,
        agent_name: str,
        project_id: int | None,
        tier: TaskTier,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        """Return (acceptance_rate, sample_size) for recent runs.

        Rate is None if no history exists.
        """
        project_filter = (
            RoutingHistoryEntry.project_id == project_id
            if project_id is not None
            else RoutingHistoryEntry.project_id.is_(None)
        )
        subq = (
            select(RoutingHistoryEntry.accepted)
            .where(
                RoutingHistoryEntry.agent_name == agent_name,
                project_filter,
                RoutingHistoryEntry.tier_used == tier,
            )
            .order_by(RoutingHistoryEntry.created_at.desc())
            .limit(limit)
            .subquery()
        )
        stmt = select(
            func.count().label("total"),
            func.count().filter(subq.c.accepted.is_(True)).label("accepted"),
        ).select_from(subq)
        result = await self._db.execute(stmt)
        row = result.one()
        total = int(row.total)
        if total == 0:
            return None, 0
        return int(row.accepted) / total, total


# ── Adaptive Routing Logic ──

_TIER_ORDER: list[TaskTier] = ["lightweight", "standard", "complex"]

MIN_SAMPLES = 10  # Minimum runs before adaptive routing kicks in
DOWNGRADE_THRESHOLD = 0.9  # >90% acceptance on lower tier → downgrade
UPGRADE_THRESHOLD = 0.7  # <70% acceptance on current tier → upgrade


def tier_below(tier: TaskTier) -> TaskTier | None:
    """Return one tier lower, or None if already at lowest."""
    idx = _TIER_ORDER.index(tier)
    return _TIER_ORDER[idx - 1] if idx > 0 else None


def tier_above(tier: TaskTier) -> TaskTier | None:
    """Return one tier higher, or None if already at highest."""
    idx = _TIER_ORDER.index(tier)
    return _TIER_ORDER[idx + 1] if idx < len(_TIER_ORDER) - 1 else None


async def resolve_adaptive_tier(
    default_tier: TaskTier,
    agent_name: str,
    project_id: int | None,
    repo: RoutingHistoryRepository,
) -> TaskTier:
    """Decide the effective tier based on historical performance.

    Algorithm:
    1. Check if a lower tier has sufficient history with high acceptance → downgrade
    2. Check if current tier is underperforming → upgrade
    3. Otherwise keep default tier
    """
    # Try downgrade — check if lower tier already performs well
    lower = tier_below(default_tier)
    if lower is not None:
        rate, count = await repo.get_acceptance_rate(agent_name, project_id, lower)
        if rate is not None and count >= MIN_SAMPLES and rate > DOWNGRADE_THRESHOLD:
            logger.info(
                "routing.adaptive_downgrade",
                agent=agent_name,
                project_id=project_id,
                from_tier=default_tier,
                to_tier=lower,
                acceptance_rate=round(rate, 3),
                sample_size=count,
            )
            return lower

    # Check if current tier is underperforming — upgrade
    rate, count = await repo.get_acceptance_rate(agent_name, project_id, default_tier)
    if rate is not None and count >= MIN_SAMPLES and rate < UPGRADE_THRESHOLD:
        higher = tier_above(default_tier)
        if higher is not None:
            logger.info(
                "routing.adaptive_upgrade",
                agent=agent_name,
                project_id=project_id,
                from_tier=default_tier,
                to_tier=higher,
                acceptance_rate=round(rate, 3),
                sample_size=count,
            )
            return higher

    return default_tier
