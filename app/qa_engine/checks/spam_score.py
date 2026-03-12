"""Spam score check for email content."""

import re

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

SPAM_TRIGGERS = [
    "buy now",
    "free",
    "click here",
    "act now",
    "limited time",
    "100%",
    "guarantee",
    "no obligation",
    "winner",
    "congratulations",
]
_DEFAULT_DEDUCTION = 0.15
_DEFAULT_THRESHOLD = 0.5


class SpamScoreCheck:
    """Checks email content for common spam trigger words."""

    name = "spam_score"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        triggers: list[str] = (
            config.params.get("triggers", SPAM_TRIGGERS) if config else SPAM_TRIGGERS
        )
        deduction: float = (
            config.params.get("deduction_per_trigger", _DEFAULT_DEDUCTION)
            if config
            else _DEFAULT_DEDUCTION
        )
        threshold: float = config.threshold if config else _DEFAULT_THRESHOLD

        text = re.sub(r"<[^>]+>", " ", html).lower()
        found = [trigger for trigger in triggers if trigger in text]
        score = max(0.0, 1.0 - len(found) * deduction)
        passed = score >= threshold
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details=f"Spam triggers found: {', '.join(found)}" if found else None,
            severity="warning" if found else "info",
        )
