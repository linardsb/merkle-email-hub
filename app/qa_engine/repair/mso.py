"""Stage 2: MSO conditional repair — wraps existing mso_repair module."""

from __future__ import annotations

from app.qa_engine.repair.pipeline import RepairResult


class MSORepair:
    """Fix MSO conditional issues using existing repair infrastructure."""

    @property
    def name(self) -> str:
        return "mso"

    def repair(self, html: str) -> RepairResult:
        from app.ai.agents.outlook_fixer.mso_repair import repair_mso_issues
        from app.qa_engine.mso_parser import validate_mso_conditionals

        mso_result = validate_mso_conditionals(html)
        if mso_result.is_valid:
            return RepairResult(html=html)

        repaired, repair_descriptions = repair_mso_issues(html, mso_result)
        repairs = [f"mso_{d.lower().replace(' ', '_')[:50]}" for d in repair_descriptions]

        return RepairResult(html=repaired, repairs_applied=repairs)
