"""Image optimization check — comprehensive DOM-parsed image validation."""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html

# Import custom checks to ensure image check functions are registered
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.image_analyzer import clear_image_cache
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "image_optimization.yaml"


class ImageOptimizationCheck:
    """Comprehensive image validation for HTML emails.

    DOM-parsed analysis of all <img> elements covering:
    - Core attributes (src, alt, width, height)
    - Format validation (banned formats, oversized data URIs)
    - Dimension integrity (numeric values only)
    - Tracking pixel accessibility
    - Rendering best practices (border="0", display:block)

    Uses YAML rule engine with 10 rules across 6 groups.
    """

    name = "image_optimization"

    def __init__(self) -> None:
        self._rules = load_rules(_RULES_PATH)
        self._engine = RuleEngine(self._rules)

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        clear_image_cache()

        try:
            doc = lxml_html.document_fromstring(html)
        except Exception:
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="Failed to parse HTML for image analysis",
                severity="error",
            )

        issues, total_deduction = self._engine.evaluate(doc, html, config)

        score = max(0.0, round(1.0 - total_deduction, 2))
        failure_issues = [i for i in issues if not i.startswith("Images:")]
        passed = len(failure_issues) == 0

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details="; ".join(issues) if issues else "All images properly optimized",
            severity="error" if total_deduction >= 0.30 else ("warning" if not passed else "info"),
        )
