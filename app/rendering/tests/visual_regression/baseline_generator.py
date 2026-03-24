"""Generate baseline screenshots for visual regression testing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.core.logging import get_logger
from app.rendering.local.emulators import _EMULATORS
from app.rendering.local.profiles import CLIENT_PROFILES
from app.rendering.local.runner import capture_screenshot
from app.rendering.tests.visual_regression.schemas import (
    BaselineManifest,
    BaselineResult,
)

logger = get_logger(__name__)

# 5 golden templates selected for visual diversity:
# 1. Simple text-only (minimal CSS)
# 2. Hero image + CTA (common marketing pattern)
# 3. Multi-column product grid (complex table layout)
# 4. Dark mode enabled (tests dark mode emulation)
# 5. Progressive enhancement (flexbox with MSO fallback)
REGRESSION_TEMPLATES: list[str] = [
    "minimal_text",
    "promotional_hero",
    "promotional_grid",
    "newsletter_2col",
    "transactional_receipt",
]

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "ai" / "templates" / "library"


def _load_template_html(slug: str) -> str:
    """Load template HTML from the golden template library."""
    path = TEMPLATE_DIR / f"{slug}.html"
    if not path.exists():
        msg = f"Template not found: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def _emulator_version_hash(client_id: str) -> str:
    """Hash emulator rule names for drift detection."""
    emulator = _EMULATORS.get(client_id)
    if not emulator:
        return "no-emulator"
    rule_names = sorted(r.name for r in emulator.rules)
    return hashlib.sha256("|".join(rule_names).encode()).hexdigest()[:16]


class BaselineGenerator:
    """Generates baseline screenshots for visual regression testing."""

    async def generate_baselines(
        self,
        templates: list[str] | None = None,
        profiles: list[str] | None = None,
        output_dir: Path | None = None,
    ) -> BaselineManifest:
        """Generate baselines for each template x profile combination.

        Args:
            templates: Template slugs to render. Defaults to REGRESSION_TEMPLATES.
            profiles: Profile IDs to render. Defaults to all CLIENT_PROFILES.
            output_dir: Output directory. Defaults to baselines/ in this package.
        """
        template_slugs = templates or REGRESSION_TEMPLATES
        profile_ids = profiles or list(CLIENT_PROFILES.keys())
        baselines_dir = output_dir or (Path(__file__).parent / "baselines")
        baselines_dir.mkdir(parents=True, exist_ok=True)

        results: list[BaselineResult] = []
        emulator_versions: dict[str, str] = {}

        for slug in template_slugs:
            html = _load_template_html(slug)
            template_dir = baselines_dir / slug
            template_dir.mkdir(parents=True, exist_ok=True)

            for profile_id in profile_ids:
                profile = CLIENT_PROFILES.get(profile_id)
                if not profile:
                    logger.warning(
                        "visual_regression.unknown_profile",
                        profile=profile_id,
                    )
                    continue

                try:
                    image_bytes = await capture_screenshot(html, profile, template_dir)
                    output_path = template_dir / f"{profile_id}.png"
                    output_path.write_bytes(image_bytes)

                    results.append(
                        BaselineResult(
                            template_slug=slug,
                            profile_id=profile_id,
                            output_path=output_path,
                            size_bytes=len(image_bytes),
                        )
                    )

                    if profile.emulator_id and profile.emulator_id not in emulator_versions:
                        emulator_versions[profile.emulator_id] = _emulator_version_hash(
                            profile.emulator_id
                        )

                except Exception:
                    logger.exception(
                        "visual_regression.baseline_failed",
                        template=slug,
                        profile=profile_id,
                    )

        # Write manifest
        manifest_data = {
            "templates": template_slugs,
            "profiles": profile_ids,
            "emulator_versions": emulator_versions,
            "baseline_count": len(results),
        }
        manifest_path = baselines_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        logger.info(
            "visual_regression.baselines_generated",
            count=len(results),
            templates=template_slugs,
            profiles=profile_ids,
        )

        return BaselineManifest(
            baselines=results,
            template_slugs=template_slugs,
            profile_ids=profile_ids,
            emulator_versions=emulator_versions,
        )
