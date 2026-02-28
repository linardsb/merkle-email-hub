"""Fallback rendering check."""

from app.qa_engine.schemas import QACheckResult


class FallbackCheck:
    """Checks for MSO conditional comments and VML fallbacks."""

    name = "fallback"

    async def run(self, html: str) -> QACheckResult:
        issues: list[str] = []

        if "<!--[if mso" not in html.lower():
            issues.append("No MSO conditional comments for Outlook fallbacks")
        if "xmlns:v=" not in html and "xmlns:o=" not in html:
            issues.append("No VML namespace declarations")

        passed = len(issues) == 0
        score = max(0.0, 1.0 - len(issues) * 0.4)
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details="; ".join(issues) if issues else None,
            severity="info",
        )
