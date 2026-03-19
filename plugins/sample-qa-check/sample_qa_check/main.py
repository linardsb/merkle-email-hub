"""Sample QA check plugin — checks for preheader/preview text element."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.api import HubPluginAPI
    from app.qa_engine.check_config import QACheckConfig
    from app.qa_engine.schemas import QACheckResult


async def check_preheader(html: str, config: QACheckConfig | None = None) -> QACheckResult:  # noqa: ARG001
    """Check that the email has a preheader/preview text element."""
    from app.qa_engine.schemas import QACheckResult

    has_preheader = bool(re.search(r'class=["\'][^"\']*preheader[^"\']*["\']', html, re.IGNORECASE))

    return QACheckResult(
        check_name="preheader_exists",
        passed=has_preheader,
        score=1.0 if has_preheader else 0.0,
        details="Preheader text element found"
        if has_preheader
        else "No preheader/preview text element detected",
        severity="warning",
    )


def setup(hub: HubPluginAPI) -> None:
    hub.qa.register_check("preheader_exists", check_preheader)
