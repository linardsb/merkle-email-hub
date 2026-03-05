"""Email on Acid API client (placeholder implementation)."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


class EoARenderingService:
    """Submits emails to Email on Acid API for cross-client rendering."""

    async def submit_test(self, html: str, subject: str, clients: list[str]) -> str:
        """Submit HTML to Email on Acid. Returns mock test ID."""
        logger.info("eoa.submit_started", subject=subject, client_count=len(clients))
        # Placeholder: real implementation would POST to EoA API
        mock_id = f"eoa_test_{hash(html) % 100000:05d}"
        logger.info("eoa.submit_completed", test_id=mock_id)
        return mock_id

    async def poll_status(self, test_id: str) -> str:
        """Poll EoA for test status. Returns 'complete' in placeholder."""
        logger.info("eoa.poll_status", test_id=test_id)
        return "complete"

    async def get_results(self, test_id: str) -> list[dict[str, str]]:
        """Get EoA screenshots. Returns mock data in placeholder."""
        logger.info("eoa.get_results", test_id=test_id)
        return [
            {
                "client_name": "gmail_web",
                "screenshot_url": f"https://placeholder.emailonacid.com/{test_id}/gmail_web.png",
                "os": "web",
                "category": "web",
            },
            {
                "client_name": "outlook_2021",
                "screenshot_url": f"https://placeholder.emailonacid.com/{test_id}/outlook_2021.png",
                "os": "windows",
                "category": "desktop",
            },
        ]
