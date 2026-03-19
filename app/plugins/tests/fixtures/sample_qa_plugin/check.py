"""Sample QA check plugin for integration testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

if TYPE_CHECKING:
    from app.plugins.api import HubPluginAPI


async def sample_link_check(html: str, config: QACheckConfig | None = None) -> QACheckResult:
    """Trivial QA check that passes if HTML contains at least one link."""
    has_link = "<a " in html.lower()
    return QACheckResult(
        check_name="sample_link_check",
        passed=has_link,
        score=1.0 if has_link else 0.0,
        details="Found link" if has_link else "No links found",
        severity="info",
    )


def setup(hub: HubPluginAPI) -> None:
    """Register the sample QA check."""
    hub.qa.register_check("sample_link_check", sample_link_check)
