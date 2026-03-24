"""Failure-Outcome Ledger — tracks recovery routing outcomes for adaptive fixer selection.

When enabled (BLUEPRINT__RECOVERY_LEDGER_ENABLED=true), records whether each
recovery fixer actually resolved the QA failure it was routed to fix.
Over time, agents with poor resolution rates are bypassed in favour of
better-performing alternatives.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── SQLAlchemy Model ──


class RecoveryOutcomeEntry(Base):
    """Records a single recovery routing outcome."""

    __tablename__ = "recovery_outcomes"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    check_name: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    agent_routed: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    failure_fingerprint: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    resolved: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    iterations_needed: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    run_id: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    project_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (sa.Index("ix_recovery_outcome_check_agent", "check_name", "agent_routed"),)


# ── Repository ──


class RecoveryOutcomeRepository:
    """CRUD for recovery outcome entries."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        check_name: str,
        agent_routed: str,
        failure_fingerprint: str | None,
        resolved: bool,
        iterations_needed: int,
        run_id: str,
        project_id: int | None,
    ) -> None:
        """Record a recovery outcome (fire-and-forget safe)."""
        entry = RecoveryOutcomeEntry(
            check_name=check_name,
            agent_routed=agent_routed,
            failure_fingerprint=failure_fingerprint,
            resolved=resolved,
            iterations_needed=iterations_needed,
            run_id=run_id,
            project_id=project_id,
        )
        self._db.add(entry)

    async def get_resolution_rate(
        self,
        check_name: str,
        agent_name: str,
        project_id: int | None,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        """Return (resolution_rate, sample_count) for recent outcomes.

        Rate is None if no history exists.
        """
        project_filter = (
            RecoveryOutcomeEntry.project_id == project_id
            if project_id is not None
            else RecoveryOutcomeEntry.project_id.is_(None)
        )
        subq = (
            select(RecoveryOutcomeEntry.resolved)
            .where(
                RecoveryOutcomeEntry.check_name == check_name,
                RecoveryOutcomeEntry.agent_routed == agent_name,
                project_filter,
            )
            .order_by(RecoveryOutcomeEntry.created_at.desc())
            .limit(limit)
            .subquery()
        )
        stmt = select(
            func.count().label("total"),
            func.count().filter(subq.c.resolved.is_(True)).label("resolved"),
        ).select_from(subq)
        result = await self._db.execute(stmt)
        row = result.one()
        total = int(row.total)
        if total == 0:
            return None, 0
        return int(row.resolved) / total, total


# ── Adaptive Selection Logic ──

MIN_OUTCOME_SAMPLES = 8
POOR_RESOLUTION_THRESHOLD = 0.30  # below this → skip agent

# Priority order for fixer fallback (mirrors recovery_router_node._FIXER_PRIORITY)
_FIXER_PRIORITY = (
    "dark_mode",
    "outlook_fixer",
    "accessibility",
    "personalisation",
    "code_reviewer",
    "scaffolder",
)


async def select_best_fixer(
    check_name: str,
    default_agent: str,
    project_id: int | None,
    repo: RecoveryOutcomeRepository,
) -> str:
    """Select the best fixer agent based on historical resolution rates.

    1. Get resolution rate for default_agent on this check_name
    2. If rate >= threshold or insufficient samples → return default_agent
    3. Otherwise, iterate _FIXER_PRIORITY candidates, pick first with rate > threshold
    4. If no candidate has data → return default_agent (static map fallback)
    """
    rate, count = await repo.get_resolution_rate(check_name, default_agent, project_id)

    # Insufficient data or acceptable performance → keep default
    if rate is None or count < MIN_OUTCOME_SAMPLES or rate >= POOR_RESOLUTION_THRESHOLD:
        return default_agent

    logger.info(
        "recovery.ledger_poor_performer",
        check_name=check_name,
        default_agent=default_agent,
        resolution_rate=round(rate, 3),
        sample_count=count,
    )

    # Try alternatives in priority order
    for candidate in _FIXER_PRIORITY:
        if candidate == default_agent:
            continue
        candidate_rate, candidate_count = await repo.get_resolution_rate(
            check_name, candidate, project_id
        )
        if (
            candidate_rate is not None
            and candidate_count >= MIN_OUTCOME_SAMPLES
            and candidate_rate >= POOR_RESOLUTION_THRESHOLD
        ):
            logger.info(
                "recovery.ledger_rerouted",
                check_name=check_name,
                from_agent=default_agent,
                to_agent=candidate,
                candidate_rate=round(candidate_rate, 3),
            )
            return candidate

    # No candidate with enough data → fall back to default
    return default_agent
