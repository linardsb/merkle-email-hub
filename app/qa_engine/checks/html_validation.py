"""HTML validation check — DOM-parsed structural validation for email HTML.

Uses the shared rule engine with rules loaded from rules/email_structure.yaml.
Complex checks delegated to custom functions in custom_checks.py.
"""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html

# Import custom checks to ensure they are registered
import app.qa_engine.custom_checks  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).parent.parent / "rules" / "email_structure.yaml"


class HtmlValidationCheck:
    """Validates HTML structure and syntax using YAML-driven rule engine.

    Loads rules from rules/email_structure.yaml covering:
    A: Document Skeleton (5 rules)
    B: Tag Integrity (3 rules)
    C: Content Integrity (2 rules)
    D: Email-Specific Structure (4 rules)
    E: Progressive Enhancement (6 rules)
    """

    name = "html_validation"

    def __init__(self) -> None:
        self._rules = load_rules(_RULES_PATH)
        self._engine = RuleEngine(self._rules)

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        """Run all structural validation checks against the provided HTML."""
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
            severity="error" if not passed else "info",
        )
