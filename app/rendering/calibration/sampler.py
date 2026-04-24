"""Calibration sampling — decides when and what to calibrate."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.rendering.calibration.repository import CalibrationRepository

settings = get_settings()


class CalibrationSampler:
    """Decides whether a client should be calibrated and selects HTML samples."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CalibrationRepository(db)

    async def should_calibrate(self, client_id: str) -> bool:
        """Check if this client should be calibrated now."""
        if not settings.rendering.calibration.enabled:
            return False

        count_today = await self.repo.count_today(client_id)
        rate_limit = settings.rendering.calibration.rate_per_client_per_day

        summary = await self.repo.get_summary(client_id)

        # New emulators (< 10 samples) get 3x rate
        if summary is None or summary.sample_count < 10:
            return count_today < rate_limit * 3

        # Stale (> 7 days since last calibration) get 2x rate
        updated_at = cast("datetime | None", summary.updated_at)
        if updated_at:
            stale_cutoff = datetime.now(UTC) - timedelta(days=7)
            if updated_at < stale_cutoff:
                return count_today < rate_limit * 2

        return count_today < rate_limit

    def select_html_for_calibration(
        self,
        candidates: list[str],
        client_id: str,
        *,
        max_selections: int = 1,
    ) -> list[str]:
        """Select deduplicated HTML samples for calibration."""
        _ = client_id  # reserved for future per-client selection logic
        seen: set[str] = set()
        selected: list[str] = []

        for html in candidates:
            prefix = hashlib.sha256(html.encode()).hexdigest()[:16]
            if prefix in seen:
                continue
            seen.add(prefix)
            selected.append(html)
            if len(selected) >= max_selections:
                break

        return selected
