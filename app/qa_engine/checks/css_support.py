"""CSS email client support check."""

from app.qa_engine.schemas import QACheckResult

UNSUPPORTED_CSS = ["position:fixed", "position:sticky", "display:grid", "display:flex"]


class CssSupportCheck:
    """Checks for CSS properties with poor email client support."""

    name = "css_support"

    async def run(self, html: str) -> QACheckResult:
        issues: list[str] = []
        html_lower = html.lower().replace(" ", "")

        for prop in UNSUPPORTED_CSS:
            if prop.replace(" ", "") in html_lower:
                issues.append(f"Unsupported CSS: {prop}")

        passed = len(issues) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(issues) * 0.25)
        return QACheckResult(
            check_name=self.name, passed=passed, score=score,
            details="; ".join(issues) if issues else None, severity="warning",
        )
