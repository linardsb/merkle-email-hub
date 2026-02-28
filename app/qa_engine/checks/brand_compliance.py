"""Brand compliance check placeholder."""

from app.qa_engine.schemas import QACheckResult


class BrandComplianceCheck:
    """Placeholder for brand compliance validation.

    In production, this would check brand colors, font usage,
    logo placement, and footer compliance against client brand guidelines.
    """

    name = "brand_compliance"

    async def run(self, html: str) -> QACheckResult:
        # Placeholder — always passes until brand rules are configured
        _ = html
        return QACheckResult(
            check_name=self.name,
            passed=True,
            score=1.0,
            details="Brand compliance check not yet configured",
            severity="info",
        )
