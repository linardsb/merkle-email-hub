"""MSO fallback rendering check — validates Outlook conditional comments, VML nesting,
namespace declarations, and ghost table structure.

Uses the shared rule engine with rules loaded from rules/mso_fallback.yaml.
Complex checks delegated to custom functions in mso_parser.py via custom_checks.py.
"""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html

# Import custom checks to ensure MSO check functions are registered
import app.qa_engine.custom_checks  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.mso_parser import clear_mso_cache
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).parent.parent / "rules" / "mso_fallback.yaml"


class FallbackCheck:
    """Validates MSO conditional comments, VML nesting, and namespace declarations.

    Loads rules from rules/mso_fallback.yaml covering:
    A: Conditional Balance (2 rules)
    B: VML Nesting (1 rule)
    C: Namespace Declarations (1 rule)
    D: Ghost Tables (1 rule)
    E: Presence Checks (3 rules)
    """

    name = "fallback"

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

        # Clear MSO parser cache before each run to avoid stale results
        clear_mso_cache()

        # Note: lxml strips comments, so most MSO checks use raw_html via custom functions.
        # We still parse DOM for the rule engine interface consistency.
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
