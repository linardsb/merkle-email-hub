"""Email client rendering change detector.

Renders feature-detection templates through Playwright (17.1),
compares against stored baselines via ODiff (17.2), and flags
when a client's CSS rendering behavior changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.ontology.feature_templates import (
    FEATURE_TEMPLATES,
    get_template_html,
    list_templates,
)
from app.rendering.local.service import LocalRenderingProvider
from app.rendering.visual_diff import compare_images

logger = get_logger(__name__)


@dataclass(frozen=True)
class RenderingChange:
    """A detected rendering behavior change for a CSS property in a client."""

    property_id: str
    client_id: str
    template_name: str
    diff_percentage: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class DetectionResult:
    """Result of a full change detection run."""

    changes: list[RenderingChange]
    templates_checked: int
    clients_checked: int
    baselines_created: int  # First-run baselines (no prior baseline existed)
    errors: int


class RenderingChangeDetector:
    """Detects rendering behavior changes by comparing screenshots against baselines.

    On first run, establishes baselines (no changes reported).
    On subsequent runs, compares current screenshots to baselines and flags differences.
    """

    def __init__(self) -> None:
        self._renderer = LocalRenderingProvider()

    async def detect_changes(
        self,
        *,
        baselines: dict[str, bytes],
    ) -> tuple[DetectionResult, dict[str, bytes]]:
        """Render all feature templates and compare against baselines.

        Args:
            baselines: dict mapping "{template_name}:{client_id}" → PNG bytes.

        Returns:
            Tuple of (DetectionResult, updated_baselines_dict).
            The updated dict includes new baselines for any template/client
            combos that didn't have one, plus updated baselines for combos
            where changes were detected.
        """
        settings = get_settings()
        threshold = settings.change_detection.diff_threshold
        target_clients = settings.change_detection.clients

        templates = list_templates()
        changes: list[RenderingChange] = []
        new_baselines: dict[str, bytes] = dict(baselines)
        baselines_created = 0
        errors = 0

        for template_name in templates:
            try:
                html = get_template_html(template_name)
            except (FileNotFoundError, OSError):
                logger.warning(
                    "change_detector.template_load_failed",
                    template=template_name,
                )
                errors += 1
                continue

            # Render across all target clients
            try:
                screenshots = await self._renderer.render_screenshots(html, clients=target_clients)
            except Exception:
                logger.error(
                    "change_detector.render_failed",
                    template=template_name,
                    exc_info=True,
                )
                errors += 1
                continue

            for result in screenshots:
                client_name = str(result["client_name"])
                image_bytes = result["image_bytes"]
                if not isinstance(image_bytes, bytes):
                    continue

                baseline_key = f"{template_name}:{client_name}"

                if baseline_key not in baselines:
                    # First run — establish baseline, no comparison
                    new_baselines[baseline_key] = image_bytes
                    baselines_created += 1
                    logger.debug(
                        "change_detector.baseline_created",
                        template=template_name,
                        client=client_name,
                    )
                    continue

                # Compare against stored baseline
                try:
                    diff = await compare_images(
                        baselines[baseline_key],
                        image_bytes,
                        threshold=threshold,
                    )
                except Exception:
                    logger.error(
                        "change_detector.diff_failed",
                        template=template_name,
                        client=client_name,
                        exc_info=True,
                    )
                    errors += 1
                    continue

                if not diff.identical:
                    property_id = FEATURE_TEMPLATES.get(template_name, template_name)
                    change = RenderingChange(
                        property_id=property_id,
                        client_id=client_name,
                        template_name=template_name,
                        diff_percentage=diff.diff_percentage,
                    )
                    changes.append(change)
                    # Update baseline to new rendering
                    new_baselines[baseline_key] = image_bytes
                    logger.info(
                        "change_detector.change_detected",
                        property_id=property_id,
                        client=client_name,
                        diff_pct=diff.diff_percentage,
                    )

        detection_result = DetectionResult(
            changes=changes,
            templates_checked=len(templates),
            clients_checked=len(target_clients),
            baselines_created=baselines_created,
            errors=errors,
        )

        return detection_result, new_baselines
