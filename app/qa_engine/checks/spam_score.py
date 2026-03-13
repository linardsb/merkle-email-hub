"""Spam score check — weighted trigger matching + formatting heuristics.

Uses the shared rule engine with rules loaded from rules/spam_score.yaml.
Trigger phrases loaded from data/spam_triggers.yaml with per-phrase weights
and categories. Custom check functions in custom_checks.py.

Implements 6 checks across 4 groups:
A (1): Trigger Phrase Matching — 50+ weighted phrases with word boundaries
B (2): Subject Line Analysis — title/meta subject scoring (3x weight multiplier)
C (3-5): Formatting Heuristics — punctuation, all-caps, obfuscation
D (6): Summary — informational, no deduction
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import html as lxml_html

# Import custom checks to ensure spam check functions are registered
import app.qa_engine.custom_checks  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).parent.parent / "rules" / "spam_score.yaml"
_TRIGGERS_PATH = Path(__file__).parent.parent / "data" / "spam_triggers.yaml"


def _load_trigger_phrases() -> list[str]:
    """Load trigger phrases for backwards-compatible SPAM_TRIGGERS export."""
    import yaml

    if not _TRIGGERS_PATH.exists():
        return []
    with _TRIGGERS_PATH.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return [str(t.get("phrase", "")) for t in data.get("triggers", [])]


SPAM_TRIGGERS: list[str] = _load_trigger_phrases()


class SpamScoreCheck:
    """Spam score validation via YAML rule engine.

    Loads rules from rules/spam_score.yaml covering 6 checks across 4 groups.
    Trigger phrases loaded from data/spam_triggers.yaml with weighted scoring.
    """

    name = "spam_score"

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
        threshold = config.threshold if config else 0.5
        passed = score >= threshold
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details="; ".join(issues) if issues else None,
            severity="warning" if not passed else "info",
        )
