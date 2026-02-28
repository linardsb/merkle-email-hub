"""Link validation check."""

import re

from app.qa_engine.schemas import QACheckResult


class LinkValidationCheck:
    """Validates links in email HTML."""

    name = "link_validation"

    async def run(self, html: str) -> QACheckResult:
        issues: list[str] = []
        hrefs = re.findall(r'href=["\']([^"\']*)["\']', html)

        for href in hrefs:
            if not href or href.startswith("#"):
                continue
            if href.startswith("http://") and "localhost" not in href:
                issues.append(f"Non-HTTPS link: {href[:80]}")
            if href == "{{" or href.startswith("{{"):
                continue  # Template variable, skip
            if not href.startswith(("http", "mailto:", "tel:", "sms:", "#", "{{", "{%")):
                issues.append(f"Invalid link protocol: {href[:80]}")

        passed = len(issues) == 0
        score = 1.0 if passed else max(0.0, 1.0 - len(issues) * 0.1)
        return QACheckResult(
            check_name=self.name, passed=passed, score=round(score, 2),
            details="; ".join(issues[:5]) if issues else None, severity="warning",
        )
