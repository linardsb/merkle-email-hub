"""Local screenshot rendering provider via Playwright CLI subprocess."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.exceptions import ScreenshotRenderError, ScreenshotTimeoutError
from app.rendering.local.confidence import RenderingConfidenceScorer
from app.rendering.local.profiles import CLIENT_PROFILES
from app.rendering.local.runner import capture_screenshot

logger = get_logger(__name__)


class LocalRenderingProvider:
    """Local screenshot rendering via Playwright CLI subprocess."""

    async def submit_test(self, html: str, subject: str, clients: list[str]) -> str:  # noqa: ARG002
        """Submit is a no-op for local — just return a UUID."""
        test_id = f"local_{uuid.uuid4().hex[:12]}"
        logger.info("local_rendering.submit", test_id=test_id, client_count=len(clients))
        return test_id

    async def poll_status(self, test_id: str) -> str:
        """Local rendering is synchronous — always 'complete'."""
        _ = test_id
        return "complete"

    async def get_results(self, test_id: str) -> list[dict[str, str]]:
        """Local provider returns empty — screenshots served via dedicated endpoint."""
        _ = test_id
        return []

    async def render_screenshots(
        self, html: str, clients: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Render HTML across client profiles, return list of results.

        Each result: {client_name, image_bytes, viewport, browser}.
        """
        settings = get_settings()
        max_clients = settings.rendering.screenshot_max_clients
        profile_names = (clients or list(CLIENT_PROFILES.keys()))[:max_clients]
        scorer = RenderingConfidenceScorer() if settings.rendering.confidence_enabled else None

        results: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="email_screenshots_") as tmpdir:
            output_dir = Path(tmpdir)
            for name in profile_names:
                profile = CLIENT_PROFILES.get(name)
                if not profile:
                    logger.warning("screenshot.unknown_profile", profile=name)
                    continue
                try:
                    image_bytes = await capture_screenshot(html, profile, output_dir)
                    confidence = scorer.score(html, profile) if scorer else None
                    results.append(
                        {
                            "client_name": name,
                            "image_bytes": image_bytes,
                            "viewport": f"{profile.viewport_width}x{profile.viewport_height}",
                            "browser": profile.browser,
                            "confidence_score": confidence.score if confidence else None,
                            "confidence_breakdown": confidence.to_dict()["breakdown"]
                            if confidence
                            else None,
                            "confidence_recommendations": confidence.recommendations
                            if confidence
                            else None,
                        }
                    )
                except (ScreenshotRenderError, ScreenshotTimeoutError, OSError) as exc:
                    logger.error(
                        "screenshot.capture_failed",
                        profile=name,
                        error=str(exc),
                    )
        return results
