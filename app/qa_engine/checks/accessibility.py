"""Email accessibility check — WCAG AA DOM-parsed validation for email HTML.

Uses the shared rule engine with rules loaded from rules/accessibility.yaml.
Complex checks delegated to custom functions in custom_checks.py.

Implements 24 checks across 8 groups:
A (1-2): Language
B (3-5): Table Semantics
C (6-8): Image Accessibility
D (9-11): Heading Hierarchy
E (12-14): Link Accessibility
F (15-20): Content Semantics & Screen Reader
G (21-22): Dark Mode Contrast
H (23-24): AMP Form Accessibility
"""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html

# Import custom checks to ensure they are registered
import app.qa_engine.custom_checks  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).parent.parent / "rules" / "accessibility.yaml"


class AccessibilityCheck:
    """Validates email HTML for WCAG AA accessibility using YAML-driven rule engine.

    Loads rules from rules/accessibility.yaml covering 24 checks across 8 groups.
    """

    name = "accessibility"

    def __init__(self) -> None:
        self._rules = load_rules(_RULES_PATH)
        self._engine = RuleEngine(self._rules)

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        """Run all accessibility checks against the provided HTML."""
        if not html or not html.strip():
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="Empty HTML document",
                severity="error",
            )

        try:
            doc = lxml_html.document_fromstring(html)
        except Exception:
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="HTML could not be parsed",
                severity="error",
            )

        issues, total_deduction = self._engine.evaluate(doc, html, config)

        score = max(0.0, round(1.0 - total_deduction, 2))
        passed = len(issues) == 0
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details="; ".join(issues) if issues else None,
            severity="warning" if not passed else "info",
        )
