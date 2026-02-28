"""HTML validation check."""

from app.qa_engine.schemas import QACheckResult


class HtmlValidationCheck:
    """Validates HTML structure and syntax."""

    name = "html_validation"

    async def run(self, html: str) -> QACheckResult:
        issues: list[str] = []

        if "<!DOCTYPE" not in html.upper():
            issues.append("Missing DOCTYPE declaration")
        if "<html" not in html.lower():
            issues.append("Missing <html> tag")
        if "</html>" not in html.lower():
            issues.append("Missing closing </html> tag")

        passed = len(issues) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(issues) * 0.2)
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details="; ".join(issues) if issues else None,
            severity="error" if not passed else "info",
        )
