"""Dark mode semantic validation — DOM-parsed + CSS-parsed checks.

Uses the shared rule engine with rules loaded from rules/dark_mode.yaml.
Complex checks delegated to custom functions in custom_checks.py via dark_mode_parser.py.

Implements 16 checks across 6 groups:
A (1-4): Meta Tag Declarations
B (5-7): Media Query Validation
C (8-10): Outlook Selectors
D (11-13): Color Coherence
E (14-15): Image Handling
F (16): Backward Compatibility
"""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html

# Import custom checks to ensure dark mode check functions are registered
import app.qa_engine.custom_checks  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.dark_mode_parser import clear_dm_cache
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).parent.parent / "rules" / "dark_mode.yaml"


class DarkModeCheck:
    """Semantic dark mode validation via YAML rule engine.

    Loads rules from rules/dark_mode.yaml covering 16 checks across 6 groups.
    """

    name = "dark_mode"

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

        # Clear dark mode parser cache before each run
        clear_dm_cache()

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
