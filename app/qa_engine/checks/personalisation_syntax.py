"""Personalisation syntax validation check.

Validates ESP-specific personalisation tags (Liquid, AMPscript, JSSP,
Django, Merge Tags, HubL, Handlebars) for correct syntax, balanced
delimiters, fallback completeness, and platform consistency.

Implements 12 rules across 6 groups:
A (1-2): Platform Detection — mixed platform, unknown platform
B (3-4): Delimiter Balance — delimiters, conditional blocks
C (5-6): Fallback Completeness — missing, empty
D (7-10): Syntax Correctness — Liquid, AMPscript, JSSP, other
E (11): Best Practices — nesting depth
F (12): Summary — informational, no deduction

L4 Reference: docs/esp_personalisation/
"""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html

# Import custom checks to ensure personalisation check functions are registered
import app.qa_engine.custom_checks  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.personalisation_validator import clear_personalisation_cache
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "personalisation_syntax.yaml"


class PersonalisationSyntaxCheck:
    """ESP personalisation syntax validation via YAML rule engine.

    Detects platform (7 ESPs), validates delimiters, checks fallbacks,
    flags mixed-platform usage, and validates syntax correctness.
    """

    name = "personalisation_syntax"

    def __init__(self) -> None:
        self._rules = load_rules(_RULES_PATH)
        self._engine = RuleEngine(self._rules)

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        if config and not config.enabled:
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details="Personalisation syntax check disabled by configuration",
                severity="info",
            )

        clear_personalisation_cache()

        if not html or not html.strip():
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details="Empty HTML document — no personalisation to validate",
                severity="info",
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
        non_summary = [i for i in issues if not i.startswith("Summary:")]
        passed = len(non_summary) == 0

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details="; ".join(issues) if issues else "No personalisation issues found",
            severity="error"
            if total_deduction >= 0.30
            else "warning"
            if total_deduction > 0
            else "info",
        )
