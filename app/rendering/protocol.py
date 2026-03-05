"""Protocol interface for rendering test providers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RenderingProvider(Protocol):
    """Protocol that rendering test services must implement.

    Each provider submits HTML to an external rendering API and
    retrieves per-client screenshots.
    """

    async def submit_test(self, html: str, subject: str, clients: list[str]) -> str:
        """Submit HTML for rendering. Returns external test ID."""
        ...

    async def poll_status(self, test_id: str) -> str:
        """Check test status. Returns 'pending', 'processing', 'complete', 'failed'."""
        ...

    async def get_results(self, test_id: str) -> list[dict[str, str]]:
        """Get screenshots for a completed test.

        Returns list of dicts with keys: client_name, screenshot_url, os, category.
        """
        ...
