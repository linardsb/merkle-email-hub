"""Emulator calibration — compares local vs external screenshots and updates seeds."""

from __future__ import annotations

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.calibration.repository import CalibrationRepository
from app.rendering.calibration.schemas import CalibrationResultSchema
from app.rendering.exceptions import CalibrationError
from app.rendering.local.confidence import _load_seeds
from app.rendering.visual_diff import compare_images

logger = get_logger(__name__)
settings = get_settings()


def _emulator_version_hash(client_id: str) -> str:
    """Hash emulator rule names for drift detection."""
    from app.rendering.local.emulators import _EMULATORS

    emulator = _EMULATORS.get(client_id)
    if not emulator:
        return "no-emulator"
    rule_names = sorted(r.name for r in emulator.rules)
    digest = hashlib.sha256("|".join(rule_names).encode()).hexdigest()
    return digest[:16]


class EmulatorCalibrator:
    """Compares local emulator screenshots against external ground truth."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CalibrationRepository(db)

    async def calibrate(
        self,
        html: str,
        client_id: str,
        local_screenshot: bytes,
        external_screenshot: bytes,
        external_provider: str,
    ) -> CalibrationResultSchema:
        """Compare a single client's local vs external screenshot."""
        html_hash = hashlib.sha256(html.encode()).hexdigest()
        emulator_version = _emulator_version_hash(client_id)

        try:
            result = await compare_images(local_screenshot, external_screenshot)
        except Exception as exc:
            raise CalibrationError(f"Image comparison failed for {client_id}: {exc}") from exc
        diff_percentage = result.diff_percentage
        accuracy_score = max(0.0, 100.0 - diff_percentage * 2)

        # Check for regression
        regression = False
        regression_details: str | None = None
        summary = await self.repo.get_summary(client_id)
        if summary and summary.sample_count > 0:
            old_accuracy = summary.current_accuracy
            threshold = settings.rendering.calibration.regression_threshold
            if (old_accuracy - accuracy_score) > threshold:
                regression = True
                regression_details = (
                    f"Accuracy dropped from {old_accuracy:.1f}% to "
                    f"{accuracy_score:.1f}% (threshold: {threshold:.1f}%)"
                )
                logger.warning(
                    "calibration.regression_detected",
                    client_id=client_id,
                    old_accuracy=old_accuracy,
                    new_accuracy=accuracy_score,
                    threshold=threshold,
                )

        await self.repo.create_record(
            client_id=client_id,
            html_hash=html_hash,
            diff_percentage=diff_percentage,
            accuracy_score=accuracy_score,
            pixel_count=result.pixel_count,
            external_provider=external_provider,
            emulator_version=emulator_version,
        )

        return CalibrationResultSchema(
            client_id=client_id,
            diff_percentage=diff_percentage,
            accuracy_score=accuracy_score,
            pixel_count=result.pixel_count,
            regression=regression,
            regression_details=regression_details,
        )

    async def calibrate_batch(
        self,
        html: str,
        local_screenshots: dict[str, bytes],
        external_screenshots: dict[str, bytes],
        external_provider: str,
    ) -> list[CalibrationResultSchema]:
        """Compare multiple clients' local vs external screenshots."""
        matched = set(local_screenshots) & set(external_screenshots)
        unmatched_local = set(local_screenshots) - matched
        unmatched_external = set(external_screenshots) - matched

        if unmatched_local:
            logger.info(
                "calibration.unmatched_local_clients",
                clients=sorted(unmatched_local),
            )
        if unmatched_external:
            logger.info(
                "calibration.unmatched_external_clients",
                clients=sorted(unmatched_external),
            )

        results: list[CalibrationResultSchema] = []
        for client_id in sorted(matched):
            result = await self.calibrate(
                html=html,
                client_id=client_id,
                local_screenshot=local_screenshots[client_id],
                external_screenshot=external_screenshots[client_id],
                external_provider=external_provider,
            )
            results.append(result)

        return results

    async def update_seeds(
        self, results: list[CalibrationResultSchema], external_provider: str = "sandbox"
    ) -> None:
        """Update calibration summaries with EMA-smoothed accuracy."""
        alpha = settings.rendering.calibration.ema_alpha
        yaml_seeds = _load_seeds()

        for result in results:
            summary = await self.repo.get_summary(result.client_id)

            if summary and summary.sample_count > 0:
                new_accuracy = (
                    1 - alpha
                ) * summary.current_accuracy + alpha * result.accuracy_score
                trend = list(summary.accuracy_trend or [])
                trend.append(round(new_accuracy, 2))
                trend = trend[-10:]
                blind_spots = list(summary.known_blind_spots or [])
                sample_count = summary.sample_count + 1
            else:
                new_accuracy = result.accuracy_score
                seed = yaml_seeds.get(result.client_id, {})
                blind_spots = list(seed.get("known_blind_spots", []))
                trend = [round(new_accuracy, 2)]
                sample_count = 1

            await self.repo.upsert_summary(
                client_id=result.client_id,
                current_accuracy=round(new_accuracy, 2),
                sample_count=sample_count,
                accuracy_trend=trend,
                known_blind_spots=blind_spots,
                last_provider=external_provider,
            )

        logger.info(
            "calibration.seeds_updated",
            clients=[r.client_id for r in results],
        )
