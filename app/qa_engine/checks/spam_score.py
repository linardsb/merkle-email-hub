"""Spam score check for email content."""

import re

from app.qa_engine.schemas import QACheckResult

SPAM_TRIGGERS = [
    "buy now", "free", "click here", "act now", "limited time",
    "100%", "guarantee", "no obligation", "winner", "congratulations",
]


class SpamScoreCheck:
    """Checks email content for common spam trigger words."""

    name = "spam_score"

    async def run(self, html: str) -> QACheckResult:
        text = re.sub(r"<[^>]+>", " ", html).lower()
        found = [trigger for trigger in SPAM_TRIGGERS if trigger in text]
        score = max(0.0, 1.0 - len(found) * 0.15)
        passed = score >= 0.5
        return QACheckResult(
            check_name=self.name, passed=passed, score=round(score, 2),
            details=f"Spam triggers found: {', '.join(found)}" if found else None,
            severity="warning" if found else "info",
        )
