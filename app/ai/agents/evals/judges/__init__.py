"""LLM judge modules for agent evaluation."""

from app.ai.agents.evals.judges.content import ContentJudge
from app.ai.agents.evals.judges.dark_mode import DarkModeJudge
from app.ai.agents.evals.judges.outlook_fixer import OutlookFixerJudge
from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge
from app.ai.agents.evals.judges.schemas import (
    CriterionResult,
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

JUDGE_REGISTRY: dict[
    str, type[ScaffolderJudge | DarkModeJudge | ContentJudge | OutlookFixerJudge]
] = {
    "scaffolder": ScaffolderJudge,
    "dark_mode": DarkModeJudge,
    "content": ContentJudge,
    "outlook_fixer": OutlookFixerJudge,
}

__all__ = [
    "JUDGE_REGISTRY",
    "ContentJudge",
    "CriterionResult",
    "DarkModeJudge",
    "JudgeCriteria",
    "JudgeInput",
    "JudgeVerdict",
    "OutlookFixerJudge",
    "ScaffolderJudge",
]
