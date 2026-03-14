"""Structured output schemas for agent decisions.

Each agent returns structured JSON (not raw HTML) when in structured mode.
Deterministic code assembles the output from these plans.
"""

from app.ai.agents.schemas.accessibility_plan import AccessibilityPlan
from app.ai.agents.schemas.build_plan import EmailBuildPlan
from app.ai.agents.schemas.code_review_plan import CodeReviewPlan
from app.ai.agents.schemas.content_plan import ContentPlan
from app.ai.agents.schemas.dark_mode_plan import DarkModePlan
from app.ai.agents.schemas.outlook_plan import OutlookFixPlan
from app.ai.agents.schemas.personalisation_plan import PersonalisationPlan

__all__ = [
    "AccessibilityPlan",
    "CodeReviewPlan",
    "ContentPlan",
    "DarkModePlan",
    "EmailBuildPlan",
    "OutlookFixPlan",
    "PersonalisationPlan",
]
