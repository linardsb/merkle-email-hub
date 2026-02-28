"""Email accessibility check."""

import re

from app.qa_engine.schemas import QACheckResult


class AccessibilityCheck:
    """Checks email HTML for basic accessibility requirements."""

    name = "accessibility"

    async def run(self, html: str) -> QACheckResult:
        issues: list[str] = []

        if "lang=" not in html.lower():
            issues.append("Missing lang attribute on <html>")
        images = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
        for img in images:
            if "alt=" not in img.lower():
                issues.append("Image missing alt attribute")
                break
        if 'role="presentation"' not in html:
            issues.append("Layout tables should use role='presentation'")

        passed = len(issues) == 0
        score = max(0.0, 1.0 - len(issues) * 0.25)
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details="; ".join(issues) if issues else None,
            severity="warning",
        )
