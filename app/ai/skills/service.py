"""Orchestration: extract → generate → store → approve/reject → eval."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.skills import amendment as amendment_mod
from app.ai.skills import extractor, repository
from app.ai.skills.exceptions import AmendmentNotFoundError
from app.ai.skills.schemas import (
    AmendmentReport,
    AmendmentStatus,
    BatchAmendmentAction,
    ExtractionResponse,
    SkillAmendment,
)
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.ai.skills.repository import SkillAmendmentRecord

logger = get_logger(__name__)


class SkillExtractionService:
    """Orchestrates pattern extraction and skill amendment lifecycle."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def extract_and_stage(
        self,
        html: str,
        source_template_id: str | None = None,
    ) -> ExtractionResponse:
        """Extract patterns from HTML and stage amendments for review.

        Args:
            html: Email template HTML to analyze.
            source_template_id: Template ID for traceability.

        Returns:
            Extraction summary with staged amendments.
        """
        settings = get_settings()

        # 1. Extract patterns (deterministic, no LLM)
        patterns = extractor.extract_patterns(html, source_template_id=source_template_id)
        logger.info(
            "skill_extraction.patterns_found",
            count=len(patterns),
            template_id=source_template_id,
        )

        # 2. Generate amendments
        amendments = amendment_mod.generate_amendments(patterns)

        # 3. Cap amendments per upload
        max_amend = settings.skill_extraction.max_amendments_per_upload
        if len(amendments) > max_amend:
            amendments.sort(key=lambda a: a.confidence, reverse=True)
            amendments = amendments[:max_amend]

        # 4. Persist to DB for review
        if amendments:
            await repository.save_amendments(self._db, amendments)
            await self._db.commit()

        logger.info(
            "skill_extraction.amendments_staged",
            patterns=len(patterns),
            amendments=len(amendments),
            template_id=source_template_id,
        )

        return ExtractionResponse(
            patterns_found=len(patterns),
            amendments_generated=len(amendments),
            amendments=amendments,
        )

    async def list_pending(
        self,
        agent_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SkillAmendment], int]:
        """List pending amendments."""
        records, total = await repository.list_pending(
            self._db, agent_name=agent_name, limit=limit, offset=offset
        )
        return [_record_to_schema(r) for r in records], total

    async def approve(self, amendment_id: str, reason: str = "") -> AmendmentReport:
        """Approve and apply a single amendment."""
        record = await repository.get_amendment(self._db, amendment_id)
        if not record:
            raise AmendmentNotFoundError(f"Amendment {amendment_id} not found")

        amendment = _record_to_schema(record)

        # Apply to skill file (not dry-run)
        report = amendment_mod.apply_amendments([amendment], dry_run=False)

        # Update status
        await repository.update_status(self._db, amendment_id, AmendmentStatus.APPLIED, reason)
        await self._db.commit()

        logger.info(
            "skill_extraction.amendment_approved",
            id=amendment_id,
            agent=record.agent_name,
        )

        # Record improvement entry for eval tracking
        settings = get_settings()
        if settings.skill_extraction.auto_eval_after_apply:
            try:
                from app.ai.agents.evals.improvement_tracker import record_improvement

                record_improvement(
                    change_description=f"Auto-extracted skill: {amendment.source_pattern_id}",
                    agent=amendment.agent_name,
                    criterion="skill_extraction",
                    before_rate=0.0,
                    after_rate=0.0,
                    task_id="25.11",
                )
            except Exception:
                logger.warning(
                    "skill_extraction.eval_tracking_failed",
                    amendment_id=amendment_id,
                    exc_info=True,
                )

        return report

    async def reject(self, amendment_id: str, reason: str = "") -> None:
        """Reject an amendment."""
        record = await repository.get_amendment(self._db, amendment_id)
        if not record:
            raise AmendmentNotFoundError(f"Amendment {amendment_id} not found")

        await repository.update_status(self._db, amendment_id, AmendmentStatus.REJECTED, reason)
        await self._db.commit()

        logger.info(
            "skill_extraction.amendment_rejected",
            id=amendment_id,
            agent=record.agent_name,
            reason=reason,
        )

    async def batch_action(
        self,
        actions: list[BatchAmendmentAction],
    ) -> tuple[int, list[dict[str, str]]]:
        """Process multiple approve/reject actions.

        Returns:
            Tuple of (processed_count, errors).
        """
        processed = 0
        errors: list[dict[str, str]] = []

        for action in actions:
            try:
                if action.action == "approve":
                    await self.approve(action.id, action.reason)
                else:
                    await self.reject(action.id, action.reason)
                processed += 1
            except AmendmentNotFoundError:
                errors.append({"id": action.id, "error": "Amendment not found"})
            except Exception:
                logger.warning(
                    "skill_extraction.batch_action_failed",
                    amendment_id=action.id,
                    exc_info=True,
                )
                await self._db.rollback()
                errors.append({"id": action.id, "error": "Internal error processing amendment"})

        return processed, errors


def _record_to_schema(record: SkillAmendmentRecord) -> SkillAmendment:
    """Convert DB record to schema."""
    return SkillAmendment(
        id=str(record.id),
        agent_name=str(record.agent_name),
        skill_file=str(record.skill_file),
        section=str(record.section),
        content=str(record.content),
        confidence=float(record.confidence),  # pyright: ignore[reportArgumentType]
        source_pattern_id=str(record.source_pattern_id),
        source_template_id=str(record.source_template_id)
        if record.source_template_id is not None
        else None,
        status=AmendmentStatus(str(record.status)),
    )
