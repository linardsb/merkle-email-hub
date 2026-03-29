"""QA check implementations for the 14-point quality gate."""

from typing import Protocol

# Import custom checks module to trigger registration of all custom check functions
import app.qa_engine.custom_checks as _custom_checks
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.checks.accessibility import AccessibilityCheck
from app.qa_engine.checks.brand_compliance import BrandComplianceCheck
from app.qa_engine.checks.css_audit import CSSAuditCheck
from app.qa_engine.checks.css_support import CssSupportCheck
from app.qa_engine.checks.dark_mode import DarkModeCheck
from app.qa_engine.checks.deliverability import DeliverabilityCheck
from app.qa_engine.checks.fallback import FallbackCheck
from app.qa_engine.checks.file_size import FileSizeCheck
from app.qa_engine.checks.html_validation import HtmlValidationCheck
from app.qa_engine.checks.image_optimization import ImageOptimizationCheck
from app.qa_engine.checks.link_validation import LinkValidationCheck
from app.qa_engine.checks.liquid_syntax import LiquidSyntaxCheck
from app.qa_engine.checks.personalisation_syntax import PersonalisationSyntaxCheck
from app.qa_engine.checks.spam_score import SpamScoreCheck
from app.qa_engine.schemas import QACheckResult


class QACheckProtocol(Protocol):
    """Protocol that all QA checks must satisfy."""

    name: str

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult: ...


ALL_CHECKS: list[QACheckProtocol] = [
    HtmlValidationCheck(),
    CssSupportCheck(),
    CSSAuditCheck(),
    FileSizeCheck(),
    LinkValidationCheck(),
    SpamScoreCheck(),
    DarkModeCheck(),
    AccessibilityCheck(),
    FallbackCheck(),
    ImageOptimizationCheck(),
    BrandComplianceCheck(),
    PersonalisationSyntaxCheck(),
    DeliverabilityCheck(),
    LiquidSyntaxCheck(),
]

__all__ = ["ALL_CHECKS"]
