"""Litmus API client (placeholder implementation)."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


class LitmusRenderingService:
    """Submits emails to Litmus Instant API for cross-client rendering."""

    async def submit_test(self, html: str, subject: str, clients: list[str]) -> str:
        """Submit HTML to Litmus. Returns mock test ID."""
        logger.info("litmus.submit_started", subject=subject, client_count=len(clients))
        # Placeholder: real implementation would POST to Litmus API
        mock_id = f"litmus_test_{hash(html) % 100000:05d}"
        logger.info("litmus.submit_completed", test_id=mock_id)
        return mock_id

    async def poll_status(self, test_id: str) -> str:
        """Poll Litmus for test status. Returns 'complete' in placeholder."""
        logger.info("litmus.poll_status", test_id=test_id)
        return "complete"

    async def get_results(self, test_id: str) -> list[dict[str, str]]:
        """Get Litmus screenshots. Returns mock data in placeholder."""
        logger.info("litmus.get_results", test_id=test_id)
        return [
            {
                "client_name": "gmail_web",
                "screenshot_url": f"https://placeholder.litmus.com/{test_id}/gmail_web.png",
                "os": "web",
                "category": "web",
            },
            {
                "client_name": "outlook_2021",
                "screenshot_url": f"https://placeholder.litmus.com/{test_id}/outlook_2021.png",
                "os": "windows",
                "category": "desktop",
            },
        ]
