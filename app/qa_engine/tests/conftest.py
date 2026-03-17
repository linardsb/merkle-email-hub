"""Shared test fixtures for the QA engine feature."""

from unittest.mock import AsyncMock

import pytest

from app.qa_engine.models import QACheck, QAOverride, QAResult
from app.qa_engine.schemas import QACheckResult
from app.shared.models import utcnow


def make_qa_result(**overrides: object) -> QAResult:
    """Factory to create a QAResult model instance with sensible defaults."""
    now = utcnow()
    defaults: dict[str, object] = {
        "id": 1,
        "build_id": None,
        "template_version_id": None,
        "overall_score": 0.85,
        "passed": False,
        "checks_passed": 8,
        "checks_total": 12,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    result = QAResult(**defaults)
    # Initialize relationships to empty to avoid lazy-load issues in tests.
    # The ORM sets defaults, but in test context we ensure they're set explicitly.
    result.checks = getattr(result, "checks", None) or []  # pyright: ignore[reportAttributeAccessIssue]
    if not hasattr(result, "override"):
        result.override = None  # pyright: ignore[reportAttributeAccessIssue]
    return result


def make_qa_check(**overrides: object) -> QACheck:
    """Factory to create a QACheck model instance with sensible defaults."""
    now = utcnow()
    defaults: dict[str, object] = {
        "id": 1,
        "qa_result_id": 1,
        "check_name": "html_validation",
        "passed": True,
        "score": 1.0,
        "details": None,
        "severity": "info",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return QACheck(**defaults)


def make_qa_override(**overrides: object) -> QAOverride:
    """Factory to create a QAOverride model instance with sensible defaults."""
    now = utcnow()
    defaults: dict[str, object] = {
        "id": 1,
        "qa_result_id": 1,
        "overridden_by_id": 1,
        "justification": "Approved by lead developer after manual review of failing checks.",
        "checks_overridden": ["dark_mode", "fallback"],
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return QAOverride(**defaults)


def make_qa_check_result(
    *,
    check_name: str = "html_validation",
    passed: bool = True,
    score: float = 1.0,
    details: str | None = None,
    severity: str = "info",
) -> QACheckResult:
    """Factory to create a QACheckResult schema instance."""
    return QACheckResult(
        check_name=check_name,
        passed=passed,
        score=score,
        details=details,
        severity=severity,
    )


@pytest.fixture
def sample_html_valid() -> str:
    """Minimal valid email HTML that passes all 11 QA checks."""
    return """<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Email</title>
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<style>
:root { color-scheme: light dark; }
@media (prefers-color-scheme: dark) {
  .dark-bg { background-color: #1a1a1a !important; }
  .dark-text { color: #e0e0e0 !important; }
}
[data-ogsc] .dark-text { color: #e0e0e0; }
[data-ogsb] .dark-bg { background-color: #1a1a1a; }
</style>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
</head>
<body>
<table role="presentation" width="600">
<tr><td><h1>Welcome</h1></td></tr>
<tr><td><img src="https://example.com/hero.png" alt="Hero image" width="600" height="300"></td></tr>
<tr><td><a href="https://example.com">Visit us</a></td></tr>
</table>
</body>
</html>"""


@pytest.fixture
def sample_html_minimal() -> str:
    """Bare-bones HTML that fails most QA checks."""
    return "<html><body><p>Hello</p></body></html>"


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock AsyncSession for repository tests."""
    return AsyncMock()
