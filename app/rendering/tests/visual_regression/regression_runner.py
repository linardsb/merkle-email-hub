"""Run visual regression tests against committed baselines."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.local.profiles import CLIENT_PROFILES, RenderingProfile
from app.rendering.local.runner import capture_screenshot
from app.rendering.tests.visual_regression.baseline_generator import (
    REGRESSION_TEMPLATES,
    _load_template_html,
)
from app.rendering.tests.visual_regression.schemas import (
    ComparisonResult,
    RegressionReport,
)
from app.rendering.visual_diff import run_odiff

logger = get_logger(__name__)


class VisualRegressionRunner:
    """Runs visual regression tests by comparing current output against baselines."""

    def __init__(
        self,
        baseline_dir: Path | None = None,
        threshold: float | None = None,
    ) -> None:
        self.baseline_dir = baseline_dir or (Path(__file__).parent / "baselines")
        settings = get_settings()
        self.threshold = (
            threshold if threshold is not None else settings.rendering.visual_regression_threshold
        )

    def _load_manifest(self) -> dict[str, list[str]] | None:
        """Load manifest.json from baseline directory."""
        manifest_path = self.baseline_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "templates": data.get("templates", REGRESSION_TEMPLATES),
            "profiles": data.get("profiles", []),
        }

    async def run(
        self,
        profiles: list[str] | None = None,
    ) -> RegressionReport:
        """Run regression against all baselines.

        For each baseline PNG:
        1. Re-render the template through the same profile
        2. Compare with ODiff
        3. Flag if diff exceeds threshold

        Args:
            profiles: Subset of profiles to test. None = all with baselines.
        """
        manifest = self._load_manifest()
        if not manifest:
            logger.warning("visual_regression.no_manifest")
            return RegressionReport(passed=True, threshold=self.threshold)

        template_slugs = manifest["templates"]
        all_profile_ids = profiles or manifest["profiles"]

        results: list[ComparisonResult] = []
        skipped: list[str] = []

        for slug in template_slugs:
            template_dir = self.baseline_dir / slug
            if not template_dir.exists():
                skipped.append(slug)
                continue

            try:
                html = _load_template_html(slug)
            except FileNotFoundError:
                logger.warning(
                    "visual_regression.template_missing",
                    template=slug,
                )
                skipped.append(slug)
                continue

            for profile_id in all_profile_ids:
                baseline_path = template_dir / f"{profile_id}.png"
                if not baseline_path.exists():
                    skipped.append(f"{slug}/{profile_id}")
                    continue

                profile = CLIENT_PROFILES.get(profile_id)
                if not profile:
                    skipped.append(f"{slug}/{profile_id}")
                    continue

                result = await self._compare_single(slug, profile_id, html, profile, baseline_path)
                results.append(result)

        passed = all(r.passed for r in results)

        report = RegressionReport(
            passed=passed,
            threshold=self.threshold,
            results=results,
            skipped=skipped,
        )

        if not passed:
            for failure in report.failures:
                logger.error(
                    "visual_regression.regression_detected",
                    template=failure.template,
                    profile=failure.profile,
                    diff_percentage=failure.diff_percentage,
                    diff_image=str(failure.diff_image_path),
                )

        logger.info(
            "visual_regression.run_complete",
            passed=passed,
            total=report.total,
            failures=len(report.failures),
            skipped=len(skipped),
        )

        return report

    async def _compare_single(
        self,
        template_slug: str,
        profile_id: str,
        html: str,
        profile: RenderingProfile,
        baseline_path: Path,
    ) -> ComparisonResult:
        """Compare a single baseline against current emulator output."""
        try:
            with tempfile.TemporaryDirectory(prefix="vr_") as tmpdir:
                output_dir = Path(tmpdir)
                current_bytes = await capture_screenshot(html, profile, output_dir)

                current_path = output_dir / f"{profile_id}_current.png"
                current_path.write_bytes(current_bytes)

                diff_output = output_dir / f"{profile_id}_diff.png"

                result = await run_odiff(
                    baseline_path,
                    current_path,
                    diff_output,
                    threshold=0.01,  # per-pixel sensitivity
                )

                passed = result.diff_percentage <= self.threshold

                # Persist diff image only on failure
                diff_image_path: Path | None = None
                if not passed and result.diff_image:
                    # Save diff to a persistent location
                    diffs_dir = self.baseline_dir / "_diffs"
                    diffs_dir.mkdir(parents=True, exist_ok=True)
                    diff_image_path = diffs_dir / f"{template_slug}__{profile_id}.png"
                    diff_image_path.write_bytes(result.diff_image)

                return ComparisonResult(
                    template=template_slug,
                    profile=profile_id,
                    diff_percentage=result.diff_percentage,
                    passed=passed,
                    diff_image_path=diff_image_path,
                )

        except Exception as exc:
            logger.exception(
                "visual_regression.comparison_error",
                template=template_slug,
                profile=profile_id,
            )
            return ComparisonResult(
                template=template_slug,
                profile=profile_id,
                diff_percentage=100.0,
                passed=False,
                diff_image_path=None,
                error=str(exc),
            )
