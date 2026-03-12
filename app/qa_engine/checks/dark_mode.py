"""Dark mode compatibility check."""

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

_DEFAULT_DEDUCTION = 0.33


class DarkModeCheck:
    """Checks for dark mode meta tag and CSS support."""

    name = "dark_mode"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        deduction: float = (
            config.params.get("deduction_per_issue", _DEFAULT_DEDUCTION)
            if config
            else _DEFAULT_DEDUCTION
        )

        issues: list[str] = []
        if "color-scheme" not in html.lower():
            issues.append("Missing color-scheme meta or CSS")
        if "prefers-color-scheme" not in html.lower():
            issues.append("No @media (prefers-color-scheme: dark) styles")
        if "[data-ogsc]" not in html and "[data-ogsb]" not in html:
            issues.append("No Outlook dark mode overrides ([data-ogsc]/[data-ogsb])")

        passed = len(issues) == 0
        score = max(0.0, 1.0 - len(issues) * deduction)
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details="; ".join(issues) if issues else None,
            severity="warning",
        )
