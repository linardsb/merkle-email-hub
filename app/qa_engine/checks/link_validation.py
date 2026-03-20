"""Link validation — DOM-parsed link extraction + URL format checking.

Uses the shared rule engine with rules loaded from rules/link_validation.yaml.
Complex checks delegated to custom functions in custom_checks.py via link_parser.py.

Implements 11 checks across 7 groups:
A (1-3): URL Protocol & Format
B (4): Empty & Suspicious
C (5): ESP Template Syntax
D (6-7): URL Encoding
E (8): Phishing Signals
F (9-10): Presence & Statistics
G (11): VML Link Coherence
"""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html

# Import custom checks to ensure link check functions are registered
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.link_parser import clear_link_cache
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).parent.parent / "rules" / "link_validation.yaml"


class LinkValidationCheck:
    """Validates links using proper HTML parsing + URL format checking."""

    name = "link_validation"

    def __init__(self) -> None:
        self._rules = load_rules(_RULES_PATH)
        self._engine = RuleEngine(self._rules)

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        if not html or not html.strip():
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="Empty HTML document",
                severity="error",
            )

        clear_link_cache()

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
