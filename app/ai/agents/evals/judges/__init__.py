"""LLM judge modules for agent evaluation."""

from app.ai.agents.evals.judges.accessibility import AccessibilityJudge
from app.ai.agents.evals.judges.code_reviewer import CodeReviewerJudge
from app.ai.agents.evals.judges.content import ContentJudge
from app.ai.agents.evals.judges.dark_mode import DarkModeJudge
from app.ai.agents.evals.judges.innovation import InnovationJudge
from app.ai.agents.evals.judges.knowledge import KnowledgeJudge
from app.ai.agents.evals.judges.outlook_fixer import OutlookFixerJudge
from app.ai.agents.evals.judges.personalisation import PersonalisationJudge
from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge
from app.ai.agents.evals.judges.schemas import (
    CriterionResult,
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)
from app.ai.agents.evals.judges.visual_qa import VisualQAJudge
from app.ai.agents.import_annotator.evals.judges.import_judge import ImportAnnotatorJudge

JUDGE_REGISTRY: dict[
    str,
    type[
        ScaffolderJudge
        | DarkModeJudge
        | ContentJudge
        | OutlookFixerJudge
        | AccessibilityJudge
        | PersonalisationJudge
        | CodeReviewerJudge
        | KnowledgeJudge
        | InnovationJudge
        | VisualQAJudge
        | ImportAnnotatorJudge
    ],
] = {
    "scaffolder": ScaffolderJudge,
    "dark_mode": DarkModeJudge,
    "content": ContentJudge,
    "outlook_fixer": OutlookFixerJudge,
    "accessibility": AccessibilityJudge,
    "personalisation": PersonalisationJudge,
    "code_reviewer": CodeReviewerJudge,
    "knowledge": KnowledgeJudge,
    "innovation": InnovationJudge,
    "visual_qa": VisualQAJudge,
    "import_annotator": ImportAnnotatorJudge,
}

__all__ = [
    "JUDGE_REGISTRY",
    "AccessibilityJudge",
    "CodeReviewerJudge",
    "ContentJudge",
    "CriterionResult",
    "DarkModeJudge",
    "ImportAnnotatorJudge",
    "InnovationJudge",
    "JudgeCriteria",
    "JudgeInput",
    "JudgeVerdict",
    "KnowledgeJudge",
    "OutlookFixerJudge",
    "PersonalisationJudge",
    "ScaffolderJudge",
    "VisualQAJudge",
]
