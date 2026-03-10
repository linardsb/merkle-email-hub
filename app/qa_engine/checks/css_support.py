"""CSS email client support check — powered by ontology."""

from app.knowledge.ontology.query import unsupported_css_in_html
from app.qa_engine.schemas import QACheckResult


class CssSupportCheck:
    """Checks for CSS properties with poor email client support.

    Powered by the email development ontology (app/knowledge/ontology/).
    Dynamically evaluates 300+ CSS properties against ~25 email clients.
    """

    name = "css_support"

    async def run(self, html: str) -> QACheckResult:
        issues = unsupported_css_in_html(html)

        # Filter to error/warning severity only (skip "info" for low-share clients)
        actionable = [i for i in issues if i["severity"] in ("error", "warning")]

        if not actionable:
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details=None,
                severity="info",
            )

        errors = [i for i in actionable if i["severity"] == "error"]
        warnings = [i for i in actionable if i["severity"] == "warning"]

        # Build human-readable details
        detail_parts: list[str] = []
        for issue in actionable[:10]:
            prop_str = f"{issue['property_name']}"
            if issue["value"]:
                prop_str += f": {issue['value']}"
            client_count = issue["unsupported_count"]
            fallback = " (fallback available)" if issue["fallback_available"] else ""
            detail_parts.append(f"Unsupported: {prop_str} ({client_count} clients){fallback}")

        if len(actionable) > 10:
            detail_parts.append(f"... and {len(actionable) - 10} more")

        # Score: deduct based on severity
        score = max(0.0, 1.0 - len(errors) * 0.2 - len(warnings) * 0.1)
        passed = len(errors) == 0
        severity = "error" if errors else "warning"

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details="; ".join(detail_parts),
            severity=severity,
        )
