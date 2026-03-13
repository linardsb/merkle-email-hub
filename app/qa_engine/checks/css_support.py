"""CSS email client support check — powered by ontology."""

from app.knowledge.ontology.query import unsupported_css_in_html
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

_DEFAULT_ERROR_DEDUCTION = 0.2
_DEFAULT_WARNING_DEDUCTION = 0.1
_DEFAULT_MAX_DETAILS = 10


class CssSupportCheck:
    """Checks for CSS properties with poor email client support.

    Powered by the email development ontology (app/knowledge/ontology/).
    Dynamically evaluates 300+ CSS properties against ~25 email clients.
    """

    name = "css_support"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        error_deduction: float = (
            config.params.get("error_deduction", _DEFAULT_ERROR_DEDUCTION)
            if config
            else _DEFAULT_ERROR_DEDUCTION
        )
        warning_deduction: float = (
            config.params.get("warning_deduction", _DEFAULT_WARNING_DEDUCTION)
            if config
            else _DEFAULT_WARNING_DEDUCTION
        )
        max_details: int = (
            config.params.get("max_issues_in_details", _DEFAULT_MAX_DETAILS)
            if config
            else _DEFAULT_MAX_DETAILS
        )

        issues = unsupported_css_in_html(html)

        # Downgrade errors to warnings when a fallback is available — the property
        # is used as progressive enhancement, not a hard dependency.
        for issue in issues:
            if issue["severity"] == "error" and issue["fallback_available"]:
                issue["severity"] = "warning"

        actionable = [i for i in issues if i["severity"] in ("error", "warning")]

        if not actionable:
            return QACheckResult(
                check_name=self.name, passed=True, score=1.0, details=None, severity="info"
            )

        errors = [i for i in actionable if i["severity"] == "error"]
        warnings = [i for i in actionable if i["severity"] == "warning"]

        detail_parts: list[str] = []
        for issue in actionable[:max_details]:
            prop_str = f"{issue['property_name']}"
            if issue["value"]:
                prop_str += f": {issue['value']}"
            client_count = issue["unsupported_count"]
            fallback = " (fallback available)" if issue["fallback_available"] else ""
            detail_parts.append(f"Unsupported: {prop_str} ({client_count} clients){fallback}")

        if len(actionable) > max_details:
            detail_parts.append(f"... and {len(actionable) - max_details} more")

        score = max(0.0, 1.0 - len(errors) * error_deduction - len(warnings) * warning_deduction)
        passed = len(errors) == 0
        severity = "error" if errors else "warning"

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details="; ".join(detail_parts),
            severity=severity,
        )
