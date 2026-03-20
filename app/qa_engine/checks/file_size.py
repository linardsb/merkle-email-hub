"""File size check for email HTML — multi-client thresholds with content breakdown."""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html

# Import custom checks to ensure file size check functions are registered
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.file_size_analyzer import clear_file_size_cache
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "file_size.yaml"


class FileSizeCheck:
    """Multi-client file size validation with content breakdown and gzip estimation.

    Evaluates HTML against Yahoo (75KB), Outlook (100KB), Gmail (102KB), and
    Braze (100KB) thresholds. Provides content breakdown analysis and gzip
    compression efficiency check.

    Uses YAML rule engine with 8 rules across 4 groups:
    - Group A: Client thresholds (Yahoo, Outlook, Gmail, Braze)
    - Group B: Content distribution (inline CSS ratio, MSO conditional ratio)
    - Group C: Compression efficiency (gzip ratio)
    - Group D: Summary (informational size breakdown)
    """

    name = "file_size"

    def __init__(self) -> None:
        self._rules = load_rules(_RULES_PATH)
        self._engine = RuleEngine(self._rules)

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        clear_file_size_cache()

        # Parse HTML — rule engine expects lxml doc even for custom-only rules
        try:
            doc = lxml_html.document_fromstring(html)
        except Exception:
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="Failed to parse HTML for file size analysis",
                severity="error",
            )

        issues, total_deduction = self._engine.evaluate(doc, html, config)

        score = max(0.0, round(1.0 - total_deduction, 2))
        # Filter out the summary line from pass/fail determination
        failure_issues = [i for i in issues if not i.startswith("Raw:")]
        passed = len(failure_issues) == 0

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details="; ".join(issues) if issues else "All file size thresholds met",
            severity="error" if total_deduction >= 0.30 else ("warning" if not passed else "info"),
        )
