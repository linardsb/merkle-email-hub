"""QA check implementations for the 10-point quality gate."""

from app.qa_engine.checks.accessibility import AccessibilityCheck
from app.qa_engine.checks.brand_compliance import BrandComplianceCheck
from app.qa_engine.checks.css_support import CssSupportCheck
from app.qa_engine.checks.dark_mode import DarkModeCheck
from app.qa_engine.checks.fallback import FallbackCheck
from app.qa_engine.checks.file_size import FileSizeCheck
from app.qa_engine.checks.html_validation import HtmlValidationCheck
from app.qa_engine.checks.image_optimization import ImageOptimizationCheck
from app.qa_engine.checks.link_validation import LinkValidationCheck
from app.qa_engine.checks.spam_score import SpamScoreCheck

ALL_CHECKS = [
    HtmlValidationCheck(),
    CssSupportCheck(),
    FileSizeCheck(),
    LinkValidationCheck(),
    SpamScoreCheck(),
    DarkModeCheck(),
    AccessibilityCheck(),
    FallbackCheck(),
    ImageOptimizationCheck(),
    BrandComplianceCheck(),
]

__all__ = ["ALL_CHECKS"]
